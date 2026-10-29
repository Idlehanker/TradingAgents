"""The rotating log setup: which files the switches turn on, and what lands in them."""

import logging
from pathlib import Path

import pytest

from webapi import logging_setup
from webapi.logging_setup import TRACE, LoggingSettings, setup_logging
from webapi.runs import RunRecord, _init_progress
from webapi.schemas import RunRequest


@pytest.fixture(autouse=True)
def _restore_logging():
    """Put the process's logging back the way the suite found it.

    ``setup_logging`` mutates the root logger, which every other test shares.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    for handler in list(root.handlers):
        if handler not in saved_handlers:
            root.removeHandler(handler)
            handler.close()
    for handler in saved_handlers:
        if handler not in root.handlers:
            root.addHandler(handler)
    root.setLevel(saved_level)
    logging_setup._settings = None
    logging_setup._signature = None


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_defaults_keep_every_level_but_trace(tmp_path):
    settings = LoggingSettings.from_env({}, log_dir=tmp_path)

    assert settings.enabled is True
    assert settings.files == {
        "debug.log": logging.DEBUG,
        "info.log": logging.INFO,
        "error.log": logging.ERROR,
    }
    assert settings.console_level == logging.INFO
    assert settings.payloads is False


def test_switches_choose_files_levels_and_rotation(tmp_path):
    env = {
        "TRADINGAGENTS_LOG_TRACE": "1",
        "TRADINGAGENTS_LOG_DEBUG": "0",
        "TRADINGAGENTS_LOG_INFO": "1",
        "TRADINGAGENTS_LOG_ERROR": "0",
        "TRADINGAGENTS_LOG_LEVEL": "warning",
        "TRADINGAGENTS_LOG_CONSOLE": "0",
        "TRADINGAGENTS_LOG_PAYLOADS": "yes",
        "TRADINGAGENTS_LOG_MAX_BYTES": "2048",
        "TRADINGAGENTS_LOG_BACKUPS": "2",
    }

    settings = LoggingSettings.from_env(env, log_dir=tmp_path)

    assert settings.files == {"trace.log": TRACE, "info.log": logging.INFO}
    assert settings.console is False
    assert settings.console_level == logging.WARNING
    assert settings.payloads is True
    assert (settings.max_bytes, settings.backups) == (2048, 2)


def test_blank_values_fall_back_to_defaults(tmp_path):
    env = {
        "TRADINGAGENTS_LOG_ENABLED": "",
        "TRADINGAGENTS_LOG_DEBUG": "",
        "TRADINGAGENTS_LOG_MAX_BYTES": "not-a-number",
    }

    settings = LoggingSettings.from_env(env, log_dir=tmp_path)

    assert settings.enabled is True
    assert "debug.log" in settings.files
    assert settings.max_bytes == 10 * 1024 * 1024


def test_each_file_is_a_level_threshold(tmp_path):
    settings = LoggingSettings.from_env(
        {"TRADINGAGENTS_LOG_TRACE": "1", "TRADINGAGENTS_LOG_CONSOLE": "0"},
        log_dir=tmp_path,
    )
    setup_logging(settings, force=True)

    logger = logging.getLogger("webapi.tests.logging")
    logger.trace("a trace line")
    logger.debug("a debug line")
    logger.info("an info line")
    logger.error("an error line")

    for handler in logging.getLogger().handlers:
        handler.flush()

    def ours(filename: str) -> list[str]:
        # The setup line itself is a DEBUG record about this very configuration.
        return [line for line in read_lines(tmp_path / filename) if "webapi.tests.logging" in line]

    assert len(ours("trace.log")) == 4
    assert "a trace line" in ours("trace.log")[0]
    assert len(ours("debug.log")) == 3
    assert len(ours("info.log")) == 2
    error_lines = ours("error.log")
    assert len(error_lines) == 1
    assert "an error line" in error_lines[0]
    # Every line carries the level, the logger name and the thread it came from.
    assert "[MainThread]" in error_lines[0]


def test_disabled_writes_nothing(tmp_path):
    settings = LoggingSettings.from_env(
        {"TRADINGAGENTS_LOG_ENABLED": "0", "TRADINGAGENTS_LOG_CONSOLE": "0"},
        log_dir=tmp_path / "logs",
    )
    setup_logging(settings, force=True)

    logging.getLogger("webapi.tests.logging").error("dropped")

    assert not (tmp_path / "logs").exists()


def test_rotation_keeps_the_configured_backups(tmp_path):
    settings = LoggingSettings.from_env(
        {
            "TRADINGAGENTS_LOG_DEBUG": "0",
            "TRADINGAGENTS_LOG_ERROR": "0",
            "TRADINGAGENTS_LOG_CONSOLE": "0",
            "TRADINGAGENTS_LOG_MAX_BYTES": "512",
            "TRADINGAGENTS_LOG_BACKUPS": "2",
        },
        log_dir=tmp_path,
    )
    setup_logging(settings, force=True)

    logger = logging.getLogger("webapi.tests.logging")
    for index in range(200):
        logger.info("record %d %s", index, "x" * 40)
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert (tmp_path / "info.log.1").exists()
    assert not (tmp_path / "info.log.3").exists()


def test_payload_switch_is_reported_to_callers(tmp_path):
    settings = LoggingSettings.from_env(
        {"TRADINGAGENTS_LOG_PAYLOADS": "1", "TRADINGAGENTS_LOG_CONSOLE": "0"},
        log_dir=tmp_path,
    )
    setup_logging(settings, force=True)

    assert logging_setup.payloads_enabled() is True
    # Payload logging does not turn TRACE on by itself: the level is still owned
    # by TRADINGAGENTS_LOG_TRACE, so the volume stays the operator's choice.
    assert logging.getLogger().isEnabledFor(TRACE) is False


def test_payloads_are_default_off(tmp_path):
    setup_logging(LoggingSettings.from_env({"TRADINGAGENTS_LOG_CONSOLE": "0"}, log_dir=tmp_path), force=True)

    assert logging_setup.payloads_enabled() is False


def make_run() -> RunRecord:
    record = RunRecord(id="trace-test", params=RunRequest(ticker="NVDA", analysis_date="2026-09-01"))
    record.selected = ["market"]
    _init_progress(record)
    return record


def flush_handlers() -> None:
    for handler in logging.getLogger().handlers:
        handler.flush()


def test_run_activity_is_traced_without_its_body(tmp_path):
    setup_logging(
        LoggingSettings.from_env({"TRADINGAGENTS_LOG_TRACE": "1", "TRADINGAGENTS_LOG_CONSOLE": "0"}, log_dir=tmp_path),
        force=True,
    )

    make_run().add_message("System", "hello trace")
    flush_handlers()

    trace_lines = read_lines(tmp_path / "trace.log")
    assert any("message type=System chars=11" in line for line in trace_lines)
    # Payload logging is off, so the text itself stays out of the log.
    assert not any("hello trace" in line for line in trace_lines)
    # Business trace never spills into the coarser files.
    assert not any("message type=" in line for line in read_lines(tmp_path / "info.log"))


def test_payload_switch_writes_the_body(tmp_path):
    setup_logging(
        LoggingSettings.from_env(
            {
                "TRADINGAGENTS_LOG_TRACE": "1",
                "TRADINGAGENTS_LOG_PAYLOADS": "1",
                "TRADINGAGENTS_LOG_CONSOLE": "0",
            },
            log_dir=tmp_path,
        ),
        force=True,
    )

    make_run().add_message("Agent", "the body itself")
    flush_handlers()

    assert any("the body itself" in line for line in read_lines(tmp_path / "trace.log"))


def test_agent_status_changes_are_logged_at_the_matching_level(tmp_path):
    setup_logging(
        LoggingSettings.from_env({"TRADINGAGENTS_LOG_CONSOLE": "0"}, log_dir=tmp_path),
        force=True,
    )

    record = make_run()
    record.update_agent("Market Analyst", "in_progress")
    record.update_agent("Market Analyst", "completed")
    record.fail("boom")
    flush_handlers()

    debug_lines = read_lines(tmp_path / "debug.log")
    assert any("agent Market Analyst: pending -> in_progress" in line for line in debug_lines)
    assert any("agent Market Analyst: in_progress -> completed" in line for line in read_lines(tmp_path / "info.log"))
    assert any("boom" in line for line in read_lines(tmp_path / "error.log"))
