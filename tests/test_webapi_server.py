"""The HTTP and WebSocket surface, exercised without running a graph.

A run is created directly in the manager, so nothing here calls a model or the
network: the server's job is to publish what the worker records.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from webapi.schemas import RunRequest
from webapi.server import create_app


@pytest.fixture(autouse=True)
def _loopback_sockets():
    """Let an event loop build its self-pipe, and nothing more.

    The suite's autouse guard refuses every ``socket.connect``. On Windows a new
    event loop builds that self-pipe over a loopback TCP pair, so the in-process
    test client cannot even start one. Everything here is served in memory, so
    restoring the real ``connect`` cannot reach the network; the monkeypatch
    that owns the guard restores its own state when the test ends.
    """
    import _socket
    import socket

    socket.socket.connect = _socket.socket.connect
    socket.socket.connect_ex = _socket.socket.connect_ex


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_config_reports_the_effective_settings(client):
    body = client.get("/api/config").json()

    assert body["analysts"][0]["key"] == "market"
    assert body["asset_types"] == ["stock", "crypto"]
    assert body["results_dir"]
    assert "backend_url" in body


def test_a_run_needs_a_ticker_and_a_date(client):
    response = client.post("/api/runs", json={"ticker": "", "analysis_date": "2026-10-01"})

    assert response.status_code == 422


def test_created_runs_are_listed_and_readable(client):
    manager = client.app.state.manager
    record = manager.create(
        RunRequest(ticker="nvda", analysis_date="2026-09-01", analysts=["market"])
    )

    listed = client.get("/api/runs").json()["runs"]
    assert listed[0]["id"] == record.id
    assert listed[0]["status"] == "queued"

    snapshot = client.get(f"/api/runs/{record.id}").json()
    assert snapshot["params"]["ticker"] == "nvda"
    assert "market_report" in snapshot["reports"]
    assert "sentiment_report" not in snapshot["reports"]
    assert client.get("/api/runs/nope").status_code == 404


def test_stream_opens_with_a_snapshot_then_deltas(client):
    manager = client.app.state.manager
    record = manager.create(RunRequest(ticker="NVDA", analysis_date="2026-09-01"))

    with client.websocket_connect(f"/ws/runs/{record.id}") as socket:
        snapshot = socket.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["data"]["id"] == record.id

        record.add_message("System", "hello from the worker")
        message = socket.receive_json()
        assert message["type"] == "message"
        assert message["data"]["message"]["content"] == "hello from the worker"

        record.update_agent("Trader", "completed")
        agents = socket.receive_json()
        assert agents["data"]["agents"]["Trader"] == "completed"


def test_stream_rejects_an_unknown_run(client):
    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect("/ws/runs/does-not-exist") as socket,
    ):
        socket.receive_json()

    assert excinfo.value.code == 4404


def test_cancel_flags_a_queued_run(client):
    manager = client.app.state.manager
    record = manager.create(RunRequest(ticker="NVDA", analysis_date="2026-09-01"))

    assert client.post(f"/api/runs/{record.id}/cancel").json() == {"cancelled": True}
    assert record.cancel_requested is True
    assert client.post("/api/runs/nope/cancel").status_code == 404
