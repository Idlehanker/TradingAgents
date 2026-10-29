"""Web API surface for TradingAgents: a FastAPI server plus the run manager.

The package is deliberately import-light: the heavy agent stack is imported
lazily inside the worker thread so starting the server stays fast.
"""

from __future__ import annotations

__all__ = ["RunManager", "RunRequest", "create_app", "setup_logging"]


def __getattr__(name: str):
    """Resolve the public names on first use, keeping import side effects away."""
    if name == "RunManager":
        from webapi.runs import RunManager

        return RunManager
    if name == "RunRequest":
        from webapi.schemas import RunRequest

        return RunRequest
    if name == "create_app":
        from webapi.server import create_app

        return create_app
    if name == "setup_logging":
        from webapi.logging_setup import setup_logging

        return setup_logging
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
