"""The outbound WAF scrubber.

A relay behind a web application firewall answers 403 to a body carrying an
attack signature, and the SDK turns that into a failed analysis step. These
tests pin what gets neutralized, that ordinary prose survives untouched, and
that the rewrite is applied to relays but never to native OpenAI.
"""
import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from tradingagents.llm_clients.openai_client import NormalizedChatOpenAI
from tradingagents.llm_clients.waf_safety import scrub_payload, scrub_text

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text", [
    "<script>alert(1)</script>",
    "union select password",
    "eval(payload)",
    'onerror="steal()"',
    "../../etc/passwd",
    "DROP TABLE users",
    "${7*7}",
])
def test_each_signature_is_neutralized(text):
    cleaned, hits = scrub_text(text)
    assert hits >= 1
    assert cleaned != text


def test_ordinary_prose_is_untouched():
    # The market analyst prompt reads like this and must arrive as written.
    prose = (
        "Your role is to select the most relevant indicators from the following "
        "list for a given market condition. 英伟达股价上涨 5%，分析师称 AI 需求强劲。"
    )
    cleaned, hits = scrub_text(prose)
    assert hits == 0
    assert cleaned == prose


def test_scrub_is_stable_when_applied_twice():
    once, _ = scrub_text("<script>alert(1)</script>")
    twice, hits = scrub_text(once)
    assert twice == once
    assert hits == 0


def test_payload_string_content_is_scrubbed():
    payload = {"messages": [{"role": "user", "content": "<script>x</script>"}]}
    assert scrub_payload(payload) >= 1
    assert "<script>" not in payload["messages"][0]["content"]


def test_payload_block_content_is_scrubbed():
    payload = {"messages": [{
        "role": "user",
        "content": [{"type": "text", "text": "an alert(1) probe"}],
    }]}
    assert scrub_payload(payload) == 1
    assert payload["messages"][0]["content"][0]["text"] == "an alert\u2011(1) probe"


def test_payload_without_messages_is_left_alone():
    assert scrub_payload({"prompt": "x"}) == 0


def _relay(**kwargs):
    return NormalizedChatOpenAI(model="m", api_key="relay-key", **kwargs)


def test_relay_request_payload_is_scrubbed():
    llm = _relay(base_url="http://localhost:8787/v1")
    payload = llm._get_request_payload([HumanMessage(content="<script>alert(1)</script>")])
    sent = payload["messages"][0]["content"]
    assert "<script>" not in sent
    assert "alert(" not in sent


def test_native_openai_payload_is_not_rewritten():
    llm = _relay()  # no base_url: the SDK's own api.openai.com
    payload = llm._get_request_payload([HumanMessage(content="<script>alert(1)</script>")])
    assert payload["messages"][0]["content"] == "<script>alert(1)</script>"


def test_system_and_human_messages_both_survive_the_rewrite():
    llm = _relay(base_url="https://relay.example/v1")
    payload = llm._get_request_payload([
        SystemMessage(content="You are a trading analyst."),
        HumanMessage(content="a union select attempt"),
    ])
    assert payload["messages"][0]["content"] == "You are a trading analyst."
    assert "union select" not in payload["messages"][1]["content"]
