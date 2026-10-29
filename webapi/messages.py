"""Turning LangChain messages into the flat records the UI renders.

These mirror the CLI's helpers in ``cli/display.py``. The web path keeps its own
copies because the CLI module pulls in ``rich`` and owns a process-wide
``message_buffer`` singleton, neither of which a per-run server can share.
"""

from __future__ import annotations

from typing import Any


def _is_empty(value: Any) -> bool:
    """Whether a value carries nothing to show.

    Text is judged by whether anything was written, not by its truthiness: a
    report saying "0" or "None" is content the run produced.
    """
    if isinstance(value, str):
        return not value.strip()
    return value is None or not bool(value)


def extract_content_string(content: Any) -> str | None:
    """Flatten str / dict / list message content into one string, or None."""
    if _is_empty(content):
        return None

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, dict):
        text = content.get("text", "")
        return text.strip() if not _is_empty(text) else None

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                parts.append(text.strip() if isinstance(text, str) else "")
            elif isinstance(item, str):
                parts.append(item.strip())
        joined = " ".join(part for part in parts if part and not _is_empty(part))
        return joined or None

    return str(content).strip() if not _is_empty(content) else None


def classify_message(message: Any) -> tuple[str, str | None]:
    """Classify a message as User / Agent / Data / Control / System and pull its text."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    content = extract_content_string(getattr(message, "content", None))

    if isinstance(message, HumanMessage):
        if content and content.strip() == "Continue":
            return "Control", content
        return "User", content

    if isinstance(message, ToolMessage):
        return "Data", content

    if isinstance(message, AIMessage):
        return "Agent", content

    return "System", content


def tool_call_records(message: Any) -> list[tuple[str, dict]]:
    """The ``(name, args)`` pairs of every tool call attached to a message."""
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return []
    records = []
    for call in tool_calls:
        if isinstance(call, dict):
            records.append((str(call.get("name", "unknown")), call.get("args") or {}))
        else:
            records.append((str(getattr(call, "name", "unknown")), getattr(call, "args", {}) or {}))
    return records
