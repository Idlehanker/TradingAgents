"""Rotating, level-split logging for the web service, switched on from ``.env``.

Four files, each one a threshold: ``trace.log`` holds everything, ``debug.log``
DEBUG and up, and so on. Every entry is mirrored into the files whose threshold
it passes, so a support bundle is one file per level rather than a single blob
that has to be filtered after the fact.

Python has no TRACE level, so one is registered here (5, below DEBUG). It is for
the step-by-step business trace — every message, chunk and event — which is too
much volume to keep on by default but is what makes a stalled run explainable.

Configuration (all optional; blank means "unset" so a copied ``.env`` works):

    TRADINGAGENTS_LOG_ENABLED      on/off switch for every file handler (default on)
    TRADINGAGENTS_LOG_DIR          where the files go (default {results_dir}/web)
    TRADINGAGENTS_LOG_TRACE        write trace.log, i.e. TRACE and up (default off)
    TRADINGAGENTS_LOG_DEBUG        write debug.log (default on)
    TRADINGAGENTS_LOG_INFO         write info.log (default on)
    TRADINGAGENTS_LOG_ERROR        write error.log (default on)
    TRADINGAGENTS_LOG_LEVEL        console level: trace/debug/info/warning/error (default info)
    TRADINGAGENTS_LOG_CONSOLE      echo to the console too (default on)
    TRADINGAGENTS_LOG_PAYLOADS     include message/report bodies, not just sizes (default off)
    TRADINGAGENTS_LOG_MAX_BYTES    rotate after this many bytes (default 10 MiB)
    TRADINGAGENTS_LOG_BACKUPS      rotated files kept per level (default 5)
    TRADINGAGENTS_LOG_LIBRARIES    let third-party loggers through at full level (default off)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

# Levels a caller may name in TRADINGAGENTS_LOG_LEVEL.
_LEVELS = {
    "trace": TRACE,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# Loggers that flood DEBUG with transport chatter when third-party output is off.
# uvicorn's own protocol trace ("connection is CLOSED" per socket) is the worst
# offender here: it says nothing about a run and buries what does.
_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "urllib3",
    "yfinance",
    "peewee",
    "asyncio",
    "openai",
    "anthropic",
    "google_genai",
    "langchain",
    "langgraph",
    "langsmith",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
)

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s [%(threadName)s] %(message)s"

_TRUE = ("1", "true", "yes", "on", "y")
_FALSE = ("0", "false", "no", "off", "n")


def _raw(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = _raw(env, name)
    if value is None:
        return default
    lowered = value.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    return default


def _number(env: Mapping[str, str], name: str, default: int) -> int:
    value = _raw(env, name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _level(env: Mapping[str, str], name: str, default: int) -> int:
    value = _raw(env, name)
    if value is None:
        return default
    return _LEVELS.get(value.lower(), default)


def level_name(level: int) -> str:
    return logging.getLevelName(level)


@dataclass
class LoggingSettings:
    """What the environment asked for; also the record of what was installed."""

    enabled: bool = True
    log_dir: Path = Path("logs")
    files: dict[str, int] = field(default_factory=dict)
    console: bool = True
    console_level: int = logging.INFO
    payloads: bool = False
    max_bytes: int = 10 * 1024 * 1024
    backups: int = 5
    libraries: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, log_dir: Path | None = None) -> LoggingSettings:
        source = os.environ if env is None else env

        files: dict[str, int] = {}
        if _flag(source, "TRADINGAGENTS_LOG_TRACE", False):
            files["trace.log"] = TRACE
        if _flag(source, "TRADINGAGENTS_LOG_DEBUG", True):
            files["debug.log"] = logging.DEBUG
        if _flag(source, "TRADINGAGENTS_LOG_INFO", True):
            files["info.log"] = logging.INFO
        if _flag(source, "TRADINGAGENTS_LOG_ERROR", True):
            files["error.log"] = logging.ERROR

        directory = log_dir
        if directory is None:
            configured = _raw(source, "TRADINGAGENTS_LOG_DIR")
            if configured:
                directory = Path(os.path.expanduser(configured))
            else:
                from tradingagents.default_config import DEFAULT_CONFIG

                directory = Path(DEFAULT_CONFIG["results_dir"]) / "web"

        return cls(
            enabled=_flag(source, "TRADINGAGENTS_LOG_ENABLED", True),
            log_dir=directory,
            files=files,
            console=_flag(source, "TRADINGAGENTS_LOG_CONSOLE", True),
            console_level=_level(source, "TRADINGAGENTS_LOG_LEVEL", logging.INFO),
            payloads=_flag(source, "TRADINGAGENTS_LOG_PAYLOADS", False),
            max_bytes=max(1024, _number(source, "TRADINGAGENTS_LOG_MAX_BYTES", 10 * 1024 * 1024)),
            backups=max(0, _number(source, "TRADINGAGENTS_LOG_BACKUPS", 5)),
            libraries=_flag(source, "TRADINGAGENTS_LOG_LIBRARIES", False),
        )

    def signature(self) -> tuple:
        return (
            self.enabled,
            str(self.log_dir),
            tuple(sorted(self.files.items())),
            self.console,
            self.console_level,
            self.payloads,
            self.max_bytes,
            self.backups,
            self.libraries,
        )


_settings: LoggingSettings | None = None
_signature: tuple | None = None


def current_settings() -> LoggingSettings | None:
    """The settings the handlers were built from, or None before setup."""
    return _settings


def payloads_enabled() -> bool:
    """Whether message and report bodies may be written at TRACE."""
    return bool(_settings is not None and _settings.payloads)


def is_trace_enabled() -> bool:
    """Whether anything would consume a TRACE record (cheap guard for callers)."""
    return logging.getLogger().isEnabledFor(TRACE)


def setup_logging(settings: LoggingSettings | None = None, *, force: bool = False) -> LoggingSettings:
    """Install the rotating handlers once; calling again with the same settings is a no-op.

    ``force`` rebuilds them, which tests use to point at a temporary directory.
    """
    global _settings, _signature

    resolved = settings if settings is not None else LoggingSettings.from_env()
    signature = resolved.signature()
    if not force and signature == _signature:
        return resolved

    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_tradingagents_log_handler", False):
            root.removeHandler(handler)
            handler.close()

    if not resolved.enabled:
        _settings, _signature = resolved, signature
        logging.getLogger(__name__).info("Logging is disabled by TRADINGAGENTS_LOG_ENABLED")
        return resolved

    formatter = logging.Formatter(_FORMAT)
    resolved.log_dir.mkdir(parents=True, exist_ok=True)

    thresholds = []
    for filename, threshold in resolved.files.items():
        handler = RotatingFileHandler(
            resolved.log_dir / filename,
            maxBytes=resolved.max_bytes,
            backupCount=resolved.backups,
            encoding="utf-8",
        )
        handler.setLevel(threshold)
        handler.setFormatter(formatter)
        handler._tradingagents_log_handler = True
        root.addHandler(handler)
        thresholds.append(threshold)

    if resolved.console:
        console = logging.StreamHandler()
        console.setLevel(resolved.console_level)
        console.setFormatter(formatter)
        console._tradingagents_log_handler = True
        root.addHandler(console)
        thresholds.append(resolved.console_level)

    # The root level must let through the most permissive handler, or its
    # records never reach it; each handler then filters for itself.
    root.setLevel(min(thresholds) if thresholds else logging.WARNING)

    if not resolved.libraries:
        for name in _NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)

    _settings, _signature = resolved, signature
    logging.getLogger(__name__).debug(
        "Logging installed: dir=%s files=%s console=%s payloads=%s",
        resolved.log_dir,
        ",".join(f"{name}:{level_name(level)}" for name, level in resolved.files.items()) or "none",
        resolved.console,
        resolved.payloads,
    )
    return resolved


def _logger_trace(self: logging.Logger, message, *args, **kwargs) -> None:
    """``logger.trace(...)``: the level below DEBUG."""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


if not hasattr(logging.Logger, "trace"):
    logging.Logger.trace = _logger_trace  # type: ignore[attr-defined]
