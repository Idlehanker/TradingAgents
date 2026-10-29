"""Decisions already recorded on disk, for the history panel.

``TradingAgentsGraph.record_decision`` writes each finished run to
``{results_dir}/{ticker}/TradingAgentsStrategy_logs/full_states_log_{date}.json``.
This reads them back, newest first.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

_LOGS_DIR = "TradingAgentsStrategy_logs"
_PREFIX = "full_states_log_"


def _excerpt(text: str, limit: int = 240) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def _load(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Skipping unreadable state log %s: %s", path, exc)
        return None


def list_decisions(limit: int = 30) -> list[dict]:
    """The most recent recorded decisions across every analysed ticker."""
    root = Path(DEFAULT_CONFIG["results_dir"])
    rows: list[dict] = []
    if not root.is_dir():
        return rows

    for logs_dir in root.glob(f"*/{_LOGS_DIR}"):
        ticker = logs_dir.parent.name
        for path in logs_dir.glob(f"{_PREFIX}*.json"):
            entry = _load(path)
            if entry is None:
                continue
            trade_date = path.stem[len(_PREFIX):]
            rows.append(
                {
                    "ticker": entry.get("company_of_interest") or ticker,
                    "trade_date": entry.get("trade_date") or trade_date,
                    "rating": entry.get("final_rating"),
                    "excerpt": _excerpt(entry.get("final_trade_decision") or ""),
                    "decision": entry.get("final_trade_decision") or "",
                    "run_settings": entry.get("run_settings") or {},
                    "report_dir": str(path.parent.parent),
                    "updated_at": path.stat().st_mtime,
                }
            )

    rows.sort(key=lambda row: row["updated_at"], reverse=True)
    return rows[:limit]


def get_decision(ticker: str, trade_date: str) -> dict | None:
    """One recorded decision, reports included, or None when nothing was saved."""
    from tradingagents.dataflows.symbols import safe_ticker_component

    try:
        safe_ticker = safe_ticker_component(ticker)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    path = Path(DEFAULT_CONFIG["results_dir"]) / safe_ticker / _LOGS_DIR / f"{_PREFIX}{trade_date}.json"
    if not path.is_file():
        return None
    entry = _load(path)
    if entry is None:
        return None
    return {
        "ticker": entry.get("company_of_interest") or ticker,
        "trade_date": entry.get("trade_date") or trade_date,
        "rating": entry.get("final_rating"),
        "decision": entry.get("final_trade_decision") or "",
        "run_settings": entry.get("run_settings") or {},
        "reports": {
            "market_report": entry.get("market_report") or "",
            "sentiment_report": entry.get("sentiment_report") or "",
            "news_report": entry.get("news_report") or "",
            "fundamentals_report": entry.get("fundamentals_report") or "",
            "investment_plan": entry.get("investment_plan") or "",
            "trader_investment_plan": entry.get("trader_investment_plan") or "",
            "final_trade_decision": entry.get("final_trade_decision") or "",
            "bull_history": (entry.get("investment_debate_state") or {}).get("bull_history") or "",
            "bear_history": (entry.get("investment_debate_state") or {}).get("bear_history") or "",
            "aggressive_history": (entry.get("risk_debate_state") or {}).get("aggressive_history") or "",
            "conservative_history": (entry.get("risk_debate_state") or {}).get("conservative_history") or "",
            "neutral_history": (entry.get("risk_debate_state") or {}).get("neutral_history") or "",
        },
    }
