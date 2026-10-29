"""Background run management: one analysis per worker thread, events pushed to subscribers.

Why a private copy of the CLI's progress logic: ``cli/display.py`` owns a
process-wide ``message_buffer`` singleton whose methods the CLI monkey-patches
to append to a log file, so two concurrent requests would write into each
other's view. Each :class:`RunRecord` here keeps state of its own and pushes the
same shapes the terminal view derives.

``TradingAgentsGraph`` binds its config process-wide on construction
(``set_config``), so only one graph runs at a time: queued runs wait for the
current one rather than corrupting each other's view of the config.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
import re
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any

from tradingagents.default_config import DEFAULT_CONFIG
from webapi.logging_setup import payloads_enabled
from webapi.messages import classify_message, tool_call_records
from webapi.schemas import RunRequest

log = logging.getLogger("webapi.runs")

# --- Teams and the sections each agent fills ---------------------------------

ANALYST_ORDER = ["market", "social", "news", "fundamentals"]

ANALYST_AGENT_NAMES = {
    "market": "Market Analyst",
    "social": "Sentiment Analyst",
    "news": "News Analyst",
    "fundamentals": "Fundamentals Analyst",
}

ANALYST_REPORT_MAP = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}

FIXED_AGENTS: dict[str, list[str]] = {
    "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
    "Trading Team": ["Trader"],
    "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
    "Portfolio Management": ["Portfolio Manager"],
}

TEAMS: dict[str, list[str]] = {
    "Analyst Team": ["Market Analyst", "Sentiment Analyst", "News Analyst", "Fundamentals Analyst"],
    **FIXED_AGENTS,
}

# section key -> (title, agent who signs it off)
SECTIONS: dict[str, tuple[str, str]] = {
    "market_report": ("Market Analysis", "Market Analyst"),
    "sentiment_report": ("Social Sentiment", "Sentiment Analyst"),
    "news_report": ("News Analysis", "News Analyst"),
    "fundamentals_report": ("Fundamentals Analysis", "Fundamentals Analyst"),
    "bull_history": ("Bull Researcher", "Bull Researcher"),
    "bear_history": ("Bear Researcher", "Bear Researcher"),
    "investment_plan": ("Research Manager", "Research Manager"),
    "trader_investment_plan": ("Trading Plan", "Trader"),
    "risk_aggressive": ("Aggressive Analyst", "Aggressive Analyst"),
    "risk_conservative": ("Conservative Analyst", "Conservative Analyst"),
    "risk_neutral": ("Neutral Analyst", "Neutral Analyst"),
    "final_trade_decision": ("Portfolio Manager Decision", "Portfolio Manager"),
}

MAX_MESSAGES = 500
MAX_TOOL_CALLS = 500


def _now() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


def _short(value: Any, limit: int = 400) -> Any:
    """Trim very long strings before they cross the wire and sit in a list row."""
    if isinstance(value, str) and len(value) > limit:
        return value[: limit - 3] + "..."
    return value


# --- The run itself ----------------------------------------------------------


@dataclass
class RunRecord:
    """Everything one analysis produces, plus the subscribers watching it."""

    id: str
    params: RunRequest
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    messages: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    agent_status: dict[str, str] = field(default_factory=dict)
    reports: dict[str, str] = field(default_factory=dict)
    selected: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(
        default_factory=lambda: {"llm_calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}
    )
    decision: dict | None = None
    report_path: str | None = None

    _processed: set = field(default_factory=set)
    _cancel: threading.Event = field(default_factory=threading.Event)
    _subscribers: set = field(default_factory=set)
    _loop: asyncio.AbstractEventLoop | None = None
    _seq: int = 0

    # -- lifecycle ----------------------------------------------------------

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else time.time()
        return max(0.0, end - self.started_at)

    @property
    def cancel_requested(self) -> bool:
        return self._cancel.is_set()

    def request_cancel(self) -> None:
        self._cancel.set()

    def set_status(self, status: str) -> None:
        if self.status == status:
            return
        log.info("run=%s status %s -> %s", self.id, self.status, status)
        self.status = status
        self.emit("status", {"status": status})

    def finish(self, status: str) -> None:
        self.finished_at = self.finished_at or time.time()
        log.info("run=%s finished as %s after %.1fs", self.id, status, self.elapsed)
        self.status = status
        self.emit("status", {"status": status})

    # -- content ------------------------------------------------------------

    def add_message(self, msg_type: str, content: str) -> None:
        entry = {"ts": _now(), "type": msg_type, "content": content}
        self.messages.append(entry)
        if len(self.messages) > MAX_MESSAGES:
            del self.messages[: len(self.messages) - MAX_MESSAGES]
        if payloads_enabled():
            log.trace("run=%s message type=%s chars=%d body=%r", self.id, msg_type, len(content), content)
        else:
            log.trace("run=%s message type=%s chars=%d", self.id, msg_type, len(content))
        self.emit("message", {"message": entry})

    def add_tool_call(self, name: str, args: dict) -> None:
        entry = {
            "ts": _now(),
            "name": name,
            "args": {k: _short(v) for k, v in (args or {}).items()},
        }
        self.tool_calls.append(entry)
        if len(self.tool_calls) > MAX_TOOL_CALLS:
            del self.tool_calls[: len(self.tool_calls) - MAX_TOOL_CALLS]
        if payloads_enabled():
            log.debug("run=%s tool call %s args=%r", self.id, name, entry["args"])
        else:
            log.debug("run=%s tool call %s args=%s", self.id, name, ",".join(entry["args"]) or "none")
        self.emit("tool_call", {"tool_call": entry})

    def update_agent(self, agent: str, status: str) -> None:
        if agent not in self.agent_status or self.agent_status[agent] == status:
            return
        previous = self.agent_status[agent]
        self.agent_status[agent] = status
        level = logging.INFO if status in ("completed", "error") else logging.DEBUG
        log.log(level, "run=%s agent %s: %s -> %s", self.id, agent, previous, status)
        self.emit("agents", {"agents": dict(self.agent_status)})

    def update_report(self, section: str, content: Any) -> None:
        if section not in self.reports:
            log.trace("run=%s ignoring report for section not in this run: %s", self.id, section)
            return
        text = content if isinstance(content, str) else "\n".join(str(item) for item in content)
        if self.reports.get(section) == text:
            return
        self.reports[section] = text
        title, agent = SECTIONS[section]
        log.debug("run=%s report %s (%s) updated: %d chars", self.id, section, agent, len(text))
        if payloads_enabled():
            log.trace("run=%s report %s body=%r", self.id, section, text)
        self.emit("report", {"section": section, "title": title, "agent": agent, "content": text})

    def update_stats(self, stats: dict) -> None:
        if stats == self.stats:
            return
        self.stats = dict(stats)
        log.trace("run=%s stats %s", self.id, self.stats)
        self.emit("stats", {"stats": self.stats})

    def fail(self, message: str) -> None:
        self.error = message
        log.error("run=%s failed: %s", self.id, message.splitlines()[0] if message else "unknown error")
        self.emit("error", {"error": message})

    # -- fan-out ------------------------------------------------------------

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit(self, event_type: str, data: dict) -> None:
        """Publish to every subscriber. Safe to call from the worker thread."""
        self._seq += 1
        loop = self._loop
        if loop is None:
            log.trace("run=%s event %s dropped: no loop bound yet", self.id, event_type)
            return
        event = {"seq": self._seq, "type": event_type, "data": data, "ts": time.time()}
        log.trace("run=%s event %s seq=%d viewers=%d", self.id, event_type, self._seq, len(self._subscribers))
        # A loop that closed between the check and the call is nobody listening.
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(self._deliver, event)

    def _deliver(self, event: dict) -> None:
        for queue in list(self._subscribers):
            queue.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        """Called on the event loop: attach a new viewer to the live stream."""
        if self._loop is None:
            # A run that never went through start() (a resumed or seeded one)
            # still dispatches on the loop its viewer arrived on.
            self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        log.info("run=%s viewer attached (%d watching)", self.id, len(self._subscribers))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
        log.info("run=%s viewer detached (%d watching)", self.id, len(self._subscribers))

    # -- whole-state snapshot for REST and late WebSocket viewers -----------

    def snapshot(self) -> dict:
        agents = dict(self.agent_status)
        teams = {}
        for team, members in TEAMS.items():
            present = [agent for agent in members if agent in agents]
            if present:
                teams[team] = present
        reports = {}
        for section, (title, agent) in SECTIONS.items():
            if section not in self.reports:
                continue
            reports[section] = {
                "section": section,
                "title": title,
                "agent": agent,
                "content": self.reports.get(section),
            }
        return {
            "id": self.id,
            "params": self.params.model_dump(),
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed": self.elapsed,
            "error": self.error,
            "messages": self.messages,
            "tool_calls": self.tool_calls,
            "agents": agents,
            "teams": teams,
            "reports": reports,
            "stats": self.stats,
            "decision": self.decision,
            "report_path": self.report_path,
            "seq": self._seq,
        }

    def summary(self) -> dict:
        """One row for the run list: no message bodies."""
        completed = sum(1 for status in self.agent_status.values() if status == "completed")
        return {
            "id": self.id,
            "ticker": self.params.ticker,
            "analysis_date": self.params.analysis_date,
            "status": self.status,
            "created_at": self.created_at,
            "elapsed": self.elapsed,
            "agents_completed": completed,
            "agents_total": len(self.agent_status),
            "rating": (self.decision or {}).get("rating"),
            "error": self.error,
        }


# --- Progress logic, ported from cli/run.py ----------------------------------


def _init_progress(record: RunRecord) -> None:
    selected = [key for key in ANALYST_ORDER if key in record.selected]
    agents: dict[str, str] = {}
    for key in selected:
        agents[ANALYST_AGENT_NAMES[key]] = "pending"
    for members in FIXED_AGENTS.values():
        for agent in members:
            agents[agent] = "pending"
    record.agent_status = agents

    # One report per selected analyst, then the shared team sections, kept in
    # the order SECTIONS declares so the UI's tabs read like the run.
    wanted = {ANALYST_REPORT_MAP[key] for key in selected}
    record.reports = {
        section: None
        for section in SECTIONS
        if section not in ANALYST_REPORT_MAP.values() or section in wanted
    }


def _update_analysts(record: RunRecord, chunk: dict) -> None:
    """Each analyst runs at once and stops when its own report lands."""
    all_filed = True
    for key in record.selected:
        agent = ANALYST_AGENT_NAMES[key]
        report_key = ANALYST_REPORT_MAP[key]
        if chunk.get(report_key):
            record.update_report(report_key, chunk[report_key])
        if record.reports.get(report_key):
            record.update_agent(agent, "completed")
        else:
            record.update_agent(agent, "in_progress")
            all_filed = False

    # Analysts start together; every one marked in_progress as soon as the run starts.
    if all_filed and record.selected and record.agent_status.get("Bull Researcher") == "pending":
        record.update_agent("Bull Researcher", "in_progress")
        record.update_agent("Bear Researcher", "in_progress")


def _handle_chunk(record: RunRecord, chunk: dict) -> None:
    _update_analysts(record, chunk)

    debate = chunk.get("investment_debate_state") or {}
    bull, bear = (debate.get("bull_history") or "").strip(), (debate.get("bear_history") or "").strip()
    plan = (chunk.get("investment_plan") or "").strip()
    if bull:
        record.update_report("bull_history", bull)
        record.update_agent("Bull Researcher", "in_progress")
    if bear:
        record.update_report("bear_history", bear)
        record.update_agent("Bear Researcher", "in_progress")
    if bull or bear:
        record.update_agent("Research Manager", "in_progress")
    if plan:
        record.update_report("investment_plan", plan)
        record.update_agent("Bull Researcher", "completed")
        record.update_agent("Bear Researcher", "completed")
        record.update_agent("Research Manager", "completed")
        record.update_agent("Trader", "in_progress")

    if chunk.get("trader_investment_plan"):
        record.update_report("trader_investment_plan", chunk["trader_investment_plan"])
        if record.agent_status.get("Trader") != "completed":
            record.update_agent("Trader", "completed")
            record.update_agent("Aggressive Analyst", "in_progress")

    risk = chunk.get("risk_debate_state") or {}
    for key, agent in (
        ("aggressive_history", "Aggressive Analyst"),
        ("conservative_history", "Conservative Analyst"),
        ("neutral_history", "Neutral Analyst"),
    ):
        content = (risk.get(key) or "").strip()
        if content:
            record.update_report(f"risk_{key.split('_')[0]}", content)
            if record.agent_status.get(agent) != "completed":
                record.update_agent(agent, "in_progress")

    decision = (chunk.get("final_trade_decision") or "").strip()
    if decision and record.agent_status.get("Portfolio Manager") != "completed":
        record.update_report("final_trade_decision", decision)
        record.update_agent("Portfolio Manager", "in_progress")
        for agent in ("Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"):
            record.update_agent(agent, "completed")
        record.update_agent("Portfolio Manager", "completed")


def _handle_messages(record: RunRecord, messages: list) -> None:
    for message in messages:
        msg_id = getattr(message, "id", None)
        if msg_id is not None:
            if msg_id in record._processed:
                log.trace("run=%s skipping already-seen message %s", record.id, msg_id)
                continue
            record._processed.add(msg_id)

        msg_type, content = classify_message(message)
        log.trace(
            "run=%s message id=%s class=%s has_text=%s",
            record.id,
            msg_id or "none",
            msg_type,
            bool(content and content.strip()),
        )
        if content and content.strip():
            record.add_message(msg_type, content)
        for name, args in tool_call_records(message):
            record.add_tool_call(name, args)


_BOLD_FIELD = re.compile(r"^\s*[-*]?\s*\*\*(.+?)\*\*\s*[:\-]\s*(.+?)\s*$", re.MULTILINE)


def _build_decision(final_state: dict) -> dict | None:
    """Pull the ratings headline out of the Portfolio Manager's markdown."""
    from tradingagents.agents.rating import is_review, run_rating

    text = (final_state.get("final_trade_decision") or "").strip()
    if not text:
        return None

    rating = run_rating(final_state)
    fields: dict[str, str] = {}
    for label, value in _BOLD_FIELD.findall(text):
        label_key = label.strip().lower()
        if label_key not in fields:
            fields[label_key] = value.strip()
    return {
        "rating": rating,
        "is_review": is_review(rating),
        "text": text,
        "fields": fields,
    }


# --- The manager -------------------------------------------------------------


class RunManager:
    """Owns every run, serializes execution, and keeps finished runs in memory."""

    def __init__(self, max_history: int = 20) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()
        self._exec_lock = threading.Lock()
        self._max_history = max_history

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def latest(self) -> RunRecord | None:
        return self._runs[next(reversed(self._runs))] if self._runs else None

    def summaries(self) -> list[dict]:
        with self._lock:
            records = list(self._runs.values())
        return [record.summary() for record in reversed(records)]

    def create(self, params: RunRequest) -> RunRecord:
        record = RunRecord(id=uuid.uuid4().hex[:12], params=params)
        record.selected = [a.lower() for a in params.analysts if a.lower() in ANALYST_ORDER]
        _init_progress(record)
        with self._lock:
            self._runs[record.id] = record
            self._trim_locked()
        log.info(
            "run=%s created ticker=%s date=%s asset=%s analysts=%s rounds=%s/%s",
            record.id,
            params.ticker,
            params.analysis_date,
            params.asset_type,
            ",".join(record.selected) or "none",
            params.max_debate_rounds or "default",
            params.max_risk_rounds or "default",
        )
        return record

    def _trim_locked(self) -> None:
        finished = [r for r in self._runs.values() if r.status in ("completed", "failed", "cancelled")]
        overflow = len(finished) - self._max_history
        for record in finished[: max(0, overflow)]:
            log.debug("run=%s dropped from memory (keeping the newest %d)", record.id, self._max_history)
            self._runs.pop(record.id, None)

    def start(self, record: RunRecord, loop: asyncio.AbstractEventLoop) -> None:
        record.bind_loop(loop)
        thread = threading.Thread(target=self._worker, args=(record,), daemon=True, name=f"run-{record.id}")
        thread.start()
        log.info("run=%s dispatched (thread=%s)", record.id, thread.name)

    def cancel(self, run_id: str) -> bool:
        record = self._runs.get(run_id)
        if record is None or record.finished_at is not None:
            log.info("run=%s cancel ignored: %s", run_id, "unknown" if record is None else "already finished")
            return False
        record.request_cancel()
        record.add_message("System", "Cancel requested: finishing the current step")
        log.info("run=%s cancel requested", run_id)
        return True

    def delete(self, run_id: str) -> bool:
        record = self._runs.get(run_id)
        if record is None:
            return False
        record.request_cancel()
        with self._lock:
            removed = self._runs.pop(run_id, None) is not None
        log.info("run=%s removed from memory: %s", run_id, removed)
        return removed

    # -- worker -------------------------------------------------------------

    def _worker(self, record: RunRecord) -> None:
        # Only one graph at a time: TradingAgentsGraph installs process-wide
        # config, so overlapping runs would read each other's settings.
        log.debug("run=%s waiting for the execution slot", record.id)
        if not self._exec_lock.acquire(timeout=3600):
            record.fail("Timed out waiting for the previous run to finish")
            record.finish("failed")
            return
        log.debug("run=%s holds the execution slot", record.id)
        try:
            if record.cancel_requested:
                log.info("run=%s cancelled while queued", record.id)
                record.finish("cancelled")
                return
            record.started_at = record.started_at or time.time()
            record.set_status("running")
            self._run(record)
        except Exception as exc:   # keep the traceback for the UI's error panel
            log.exception("run=%s raised %s", record.id, type(exc).__name__)
            record.fail(f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}")
            record.finish("failed")
        finally:
            self._exec_lock.release()
            log.debug("run=%s released the execution slot", record.id)
            if record.finished_at is None:
                record.finish(record.status if record.status != "running" else "completed")

    def _run(self, record: RunRecord) -> None:
        from cli.stats_handler import StatsCallbackHandler
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        params = record.params
        ticker, trade_date = params.ticker.strip().upper(), params.analysis_date

        config = DEFAULT_CONFIG.copy()
        if params.quick_think_llm:
            config["quick_think_llm"] = params.quick_think_llm
        if params.deep_think_llm:
            config["deep_think_llm"] = params.deep_think_llm
        if params.max_debate_rounds:
            config["max_debate_rounds"] = params.max_debate_rounds
        if params.max_risk_rounds:
            config["max_risk_discuss_rounds"] = params.max_risk_rounds
        if params.output_language:
            config["output_language"] = params.output_language
        config["checkpoint_enabled"] = params.checkpoint_enabled

        log.info(
            "run=%s starting ticker=%s date=%s asset=%s provider=%s backend=%s deep=%s quick=%s "
            "debate_rounds=%s risk_rounds=%s language=%s checkpoint=%s",
            record.id,
            ticker,
            trade_date,
            params.asset_type,
            config["llm_provider"],
            config.get("backend_url") or "provider default",
            config["deep_think_llm"],
            config["quick_think_llm"],
            config["max_debate_rounds"],
            config["max_risk_discuss_rounds"],
            config.get("output_language"),
            bool(config.get("checkpoint_enabled")),
        )

        stats = StatsCallbackHandler()
        record.add_message("System", f"Selected ticker: {ticker}")
        record.add_message("System", f"Asset type: {params.asset_type}")
        record.add_message("System", f"Analysis date: {trade_date}")
        record.add_message("System", f"Selected analysts: {', '.join(record.selected) or 'none'}")
        record.add_message(
            "System",
            f"Models: deep={config['deep_think_llm']}, quick={config['quick_think_llm']}, "
            f"provider={config['llm_provider']}",
        )
        for key in record.selected:
            record.update_agent(ANALYST_AGENT_NAMES[key], "in_progress")

        graph = TradingAgentsGraph(record.selected, config=config, debug=False, callbacks=[stats])
        log.debug("run=%s graph built for analysts=%s", record.id, ",".join(record.selected) or "none")

        init_state = graph.create_run_state(ticker, trade_date, params.asset_type)
        args = graph.propagator.get_graph_args(callbacks=[stats])
        log.debug("run=%s initial state ready; graph args keys=%s", record.id, sorted(args))

        thread_id = graph.begin_checkpoint(ticker, trade_date, params.asset_type)
        if thread_id is not None:
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = thread_id
            resumed = "Resuming the saved run" if getattr(graph, "_resuming", False) else "Starting fresh"
            log.info("run=%s checkpoint thread=%s resumed=%s",
                     record.id, thread_id, getattr(graph, "_resuming", False))
            record.add_message("System", f"{resumed} for {ticker} on {trade_date}")

        final_state: dict = {}
        cancelled = False
        chunks = 0
        try:
            for messages, chunk in graph.stream_run(graph.checkpoint_input(init_state), **args):
                if record.cancel_requested:
                    log.info("run=%s stopping after %d chunks on request", record.id, chunks)
                    cancelled = True
                    break
                chunks += 1
                log.trace(
                    "run=%s chunk %d messages=%d keys=%s",
                    record.id,
                    chunks,
                    len(messages),
                    sorted(chunk) if isinstance(chunk, dict) else type(chunk).__name__,
                )
                _handle_messages(record, messages)
                if chunk is not None:
                    final_state.update(chunk)
                    _handle_chunk(record, chunk)
                record.update_stats(stats.get_stats())
            else:
                record.update_stats(stats.get_stats())
        finally:
            graph.end_checkpoint()

        log.info("run=%s stream ended after %d chunks (stats=%s)", record.id, chunks, stats.get_stats())

        if cancelled:
            record.add_message("System", "Run cancelled")
            record.finish("cancelled")
            return

        for agent in record.agent_status:
            record.update_agent(agent, "completed")

        # Streamed chunks are per-step deltas; only the union carries every report.
        for section in record.reports:
            if final_state.get(section):
                record.update_report(section, final_state[section])
        debate = final_state.get("investment_debate_state") or {}
        risk = final_state.get("risk_debate_state") or {}
        for key, section in (("bull_history", "bull_history"), ("bear_history", "bear_history")):
            if debate.get(key):
                record.update_report(section, debate[key])
        for key in ("aggressive_history", "conservative_history", "neutral_history"):
            if risk.get(key):
                record.update_report(f"risk_{key.split('_')[0]}", risk[key])

        record.decision = _build_decision(final_state)
        if record.decision is None:
            log.warning("run=%s finished without a final decision", record.id)
            record.add_message("System", "Run finished without a final decision")
        else:
            log.info(
                "run=%s decision rating=%s review=%s fields=%s",
                record.id,
                record.decision["rating"],
                record.decision["is_review"],
                ",".join(record.decision["fields"]) or "none",
            )
            record.emit("decision", {"decision": record.decision})

        try:
            graph.record_decision(ticker, trade_date, final_state)
            graph.clear_checkpoint_on_success(ticker, trade_date, params.asset_type)
            record.report_path = str(graph.save_reports(final_state, ticker, html=True))
            log.info("run=%s reports written to %s", record.id, record.report_path)
            record.add_message("System", f"Report saved to {record.report_path}")
        except Exception as exc:
            # A report that cannot be written should not hide a finished run.
            log.exception("run=%s could not save its reports", record.id)
            record.add_message("System", f"Could not save the report: {exc}")

        record.add_message("System", f"Completed analysis for {trade_date}")
        record.update_stats(stats.get_stats())
