"""FastAPI server behind the web GUI: REST for control, WebSocket for live progress."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from tradingagents.default_config import DEFAULT_CONFIG
from webapi import history
from webapi.logging_setup import setup_logging
from webapi.runs import ANALYST_AGENT_NAMES, ANALYST_ORDER, RunManager
from webapi.schemas import RunRequest

log = logging.getLogger("webapi.server")

DIST_DIR = Path(__file__).resolve().parent.parent / "webui" / "dist"

OUTPUT_LANGUAGES = [
    "English", "Chinese", "Japanese", "Korean", "Hindi", "Spanish",
    "Portuguese", "French", "German", "Arabic", "Russian",
]

# Served straight off disk: their request lines would bury the business log.
_STATIC_PREFIXES = ("/assets/", "/favicon")


def create_app() -> FastAPI:
    # Idempotent: the first app (or the entry point) installs the handlers.
    settings = setup_logging()
    app = FastAPI(title="TradingAgents Web GUI", version="0.1.0", docs_url="/api/docs")
    manager = RunManager()
    app.state.manager = manager
    app.state.logging = settings

    # The Vite dev server proxies here; same-origin in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        """One line per request: what was asked, what came back, how long it took."""
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("HTTP %s %s raised", request.method, request.url.path)
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        path = request.url.path
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        elif path.startswith(_STATIC_PREFIXES):
            level = logging.DEBUG
        else:
            level = logging.INFO
        log.log(
            level,
            "HTTP %s %s -> %d in %.0fms",
            request.method,
            path,
            response.status_code,
            elapsed_ms,
        )
        if request.query_params:
            log.debug("HTTP %s %s query=%s", request.method, path, dict(request.query_params))
        return response

    # -- static REST ---------------------------------------------------------

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True, "version": app.version, "busy": _busy(manager)}

    @app.get("/api/config")
    async def config() -> dict:
        cfg = DEFAULT_CONFIG
        return {
            "llm_provider": cfg.get("llm_provider"),
            "backend_url": cfg.get("backend_url"),
            "deep_think_llm": cfg.get("deep_think_llm"),
            "quick_think_llm": cfg.get("quick_think_llm"),
            "quick_think_provider": cfg.get("quick_think_provider"),
            "deep_think_provider": cfg.get("deep_think_provider"),
            "max_debate_rounds": cfg.get("max_debate_rounds"),
            "max_risk_discuss_rounds": cfg.get("max_risk_discuss_rounds"),
            "output_language": cfg.get("output_language"),
            "checkpoint_enabled": bool(cfg.get("checkpoint_enabled")),
            "results_dir": str(cfg.get("results_dir")),
            "data_cache_dir": str(cfg.get("data_cache_dir")),
            "analysts": [
                {"key": key, "label": ANALYST_AGENT_NAMES[key]} for key in ANALYST_ORDER
            ],
            "languages": OUTPUT_LANGUAGES,
            "asset_types": ["stock", "crypto"],
            "busy": _busy(manager),
        }

    @app.get("/api/runs")
    async def list_runs() -> dict:
        return {"runs": manager.summaries()}

    @app.post("/api/runs", status_code=201)
    async def create_run(payload: RunRequest) -> JSONResponse:
        record = manager.create(payload)
        manager.start(record, asyncio.get_running_loop())
        return JSONResponse(
            {"id": record.id, "status": record.status, "snapshot": record.snapshot()},
            status_code=201,
        )

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> dict:
        record = _require(manager, run_id)
        return record.snapshot()

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel_run(run_id: str) -> dict:
        _require(manager, run_id)
        return {"cancelled": manager.cancel(run_id)}

    @app.delete("/api/runs/{run_id}")
    async def delete_run(run_id: str) -> dict:
        _require(manager, run_id)
        return {"deleted": manager.delete(run_id)}

    @app.get("/api/history")
    async def list_history(limit: int = 30) -> dict:
        try:
            rows = history.list_decisions(limit)
        except OSError as exc:
            raise HTTPException(
                status_code=500, detail=f"Cannot read results directory: {exc}"
            ) from exc
        log.debug("history: %d recorded decisions", len(rows))
        return {"decisions": rows}

    @app.get("/api/history/{ticker}/{trade_date}")
    async def get_past_decision(ticker: str, trade_date: str) -> dict:
        try:
            entry = history.get_decision(ticker, trade_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if entry is None:
            log.warning("no recorded decision for %s on %s", ticker, trade_date)
            raise HTTPException(status_code=404, detail="No recorded decision for that ticker and date")
        log.info("history: served %s on %s (rating=%s)", ticker, trade_date, entry.get("rating"))
        return entry

    # -- live stream ---------------------------------------------------------

    @app.websocket("/ws/runs/{run_id}")
    async def stream_run(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        record = manager.get(run_id)
        if record is None:
            log.warning("ws: rejected viewer for unknown run %s", run_id)
            # Accept first: an unaccepted close is reported as a 403 handshake
            # failure, which hides the reason from the client.
            await websocket.close(code=4404)
            return

        log.info("ws: viewer connected to run=%s (status=%s)", run_id, record.status)
        snapshot = record.snapshot()
        await websocket.send_json(
            {"seq": snapshot.pop("seq"), "type": "snapshot", "data": snapshot, "ts": time.time()}
        )
        # The snapshot already carries this state: subscribe only after sending it.
        queue = record.subscribe()
        try:
            # Stay connected until the viewer leaves: a run keeps emitting after
            # its status change, and dropping the socket early would lose those.
            while True:
                event = await queue.get()
                log.trace("ws: run=%s <- %s seq=%s", run_id, event["type"], event["seq"])
                await websocket.send_json(event)
        except (WebSocketDisconnect, RuntimeError):
            log.info("ws: viewer left run=%s (status=%s)", run_id, record.status)
        finally:
            record.unsubscribe(queue)

    # -- built UI (or the dev-server note) -----------------------------------

    if DIST_DIR.is_dir():
        assets = DIST_DIR / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        async def spa(full_path: str):
            target = DIST_DIR / full_path
            if full_path and target.is_file():
                return FileResponse(target)
            index = DIST_DIR / "index.html"
            if index.is_file():
                return FileResponse(index)
            return PlainTextResponse("UI build not found.", status_code=404)

    return app


def _require(manager: RunManager, run_id: str):
    record = manager.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Unknown run")
    return record


def _busy(manager: RunManager) -> bool:
    return any(run.status in ("queued", "running") for run in manager.summaries())


app = create_app()


def main() -> None:
    """Entry point: ``tradingagents-web`` or ``python -m webapi.server``."""
    import uvicorn

    settings = setup_logging()
    port = int(os.getenv("TRADINGAGENTS_WEB_PORT", "8788"))
    host = os.getenv("TRADINGAGENTS_WEB_HOST", "127.0.0.1")
    log.info(
        "starting the web GUI on http://%s:%d (logs: %s, payloads: %s)",
        host,
        port,
        settings.log_dir if settings.enabled else "disabled",
        settings.payloads,
    )
    # log_config=None keeps uvicorn's own records (startup, shutdown, errors)
    # flowing into the same rotating files; access lines come from the
    # middleware above instead of a second, differently formatted access log.
    uvicorn.run(app, host=host, port=port, access_log=False, log_config=None)


if __name__ == "__main__":
    main()
