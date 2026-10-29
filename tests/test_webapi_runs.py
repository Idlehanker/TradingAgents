"""The web run's progress mapping, without starting a real graph.

A run is driven by the same state deltas ``stream_run`` yields, so these feed
that shape directly. Nothing here touches models or the network.
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from webapi.runs import (
    RunRecord,
    _build_decision,
    _handle_chunk,
    _handle_messages,
    _init_progress,
)
from webapi.schemas import RunRequest


def make_record(analysts=("market", "social", "news", "fundamentals")) -> RunRecord:
    request = RunRequest(ticker="NVDA", analysis_date="2026-09-01", analysts=list(analysts))
    record = RunRecord(id="test", params=request)
    record.selected = list(analysts)
    _init_progress(record)
    return record





def test_analysts_run_together_and_file_reports():
    record = make_record(["market", "news"])

    _handle_chunk(record, {"market_report": "prices look fine"})

    assert record.agent_status["Market Analyst"] == "completed"
    assert record.agent_status["News Analyst"] == "in_progress"
    assert record.reports["market_report"] == "prices look fine"
    assert record.reports["news_report"] is None
    # Analysts not selected are not part of this run at all.
    assert "Sentiment Analyst" not in record.agent_status

    _handle_chunk(record, {"news_report": "headlines are quiet"})

    assert record.agent_status["News Analyst"] == "completed"
    assert record.agent_status["Bull Researcher"] == "in_progress"


def test_debate_trader_and_risk_steps_advance_the_chain():
    record = make_record(["market"])

    _handle_chunk(record, {"market_report": "done"})
    _handle_chunk(
        record,
        {"investment_debate_state": {"bull_history": "bull view", "bear_history": "bear view"}},
    )
    assert record.agent_status["Bull Researcher"] == "in_progress"
    assert record.reports["bull_history"] == "bull view"

    _handle_chunk(record, {"investment_plan": "buy it"})
    assert record.agent_status["Research Manager"] == "completed"
    assert record.agent_status["Trader"] == "in_progress"

    _handle_chunk(record, {"trader_investment_plan": "enter long"})
    assert record.agent_status["Trader"] == "completed"
    assert record.agent_status["Aggressive Analyst"] == "in_progress"

    _handle_chunk(
        record,
        {
            "risk_debate_state": {
                "aggressive_history": "go big",
                "conservative_history": "be careful",
                "neutral_history": "balance it",
            }
        },
    )
    assert record.reports["risk_aggressive"] == "go big"
    assert record.agent_status["Neutral Analyst"] == "in_progress"

    _handle_chunk(record, {"final_trade_decision": "**Rating**: Buy"})
    assert record.agent_status["Portfolio Manager"] == "completed"
    assert record.agent_status["Aggressive Analyst"] == "completed"


def test_messages_are_recorded_once_each():
    record = make_record(["market"])
    message = AIMessage(content="hello", id="m1")

    _handle_messages(record, [message, message])

    assert [entry["content"] for entry in record.messages] == ["hello"]
    assert record.messages[0]["type"] == "Agent"


def test_message_types_follow_the_terminal_view():
    record = make_record(["market"])

    _handle_messages(
        record,
        [
            HumanMessage(content="NVDA", id="h1"),
            ToolMessage(content="price data", tool_call_id="call_1", id="t1"),
            HumanMessage(content="Continue", id="h2"),
            AIMessage(content="done", id="a1"),
        ],
    )

    assert [entry["type"] for entry in record.messages] == ["User", "Data", "Control", "Agent"]


def test_tool_calls_are_captured():
    record = make_record(["market"])
    message = AIMessage(
        content="",
        id="m2",
        tool_calls=[{"name": "get_stock_data", "args": {"ticker": "NVDA"}, "id": "call_1"}],
    )

    _handle_messages(record, [message])

    assert record.tool_calls[0]["name"] == "get_stock_data"
    assert record.tool_calls[0]["args"] == {"ticker": "NVDA"}
    assert record.messages == []


def test_decision_headline_is_read_from_the_portfolio_manager_text():
    decision = _build_decision(
        {
            "final_trade_decision": (
                "**Rating**: Buy\n**Executive Summary**: strong demand\n"
                "**Price Target**: 250\n**Time Horizon**: 3 months"
            )
        }
    )

    assert decision["rating"] == "Buy"
    assert decision["fields"]["price target"] == "250"
    assert decision["fields"]["executive summary"] == "strong demand"
    assert decision["is_review"] is False


def test_no_decision_text_means_no_decision():
    assert _build_decision({"final_trade_decision": ""}) is None


def test_snapshot_reports_only_selected_analyst_sections():
    snapshot = make_record(["market"]).snapshot()

    assert "market_report" in snapshot["reports"]
    assert "sentiment_report" not in snapshot["reports"]
    assert snapshot["status"] == "queued"
