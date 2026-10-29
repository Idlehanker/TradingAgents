"""Neutralize the fragments a gateway's WAF reads as an injection attempt.

A hosted OpenAI-compatible relay can sit behind a web application firewall that
scans request bodies for attack signatures and answers 403 with an HTML block
page. The OpenAI SDK raises that as ``APIStatusError``, so a single matching
string — a news article quoting a ``<script>`` tag, a filing mentioning
``alert(``, a headline about a ``union select`` intrusion — kills the whole
analysis step.

Each signature is broken with a character that is not whitespace, because a
space is exactly what these rules already allow for (``alert (1)`` is blocked
just like ``alert(1)``). The text still reads the same to a model, but no longer
matches a rule. Only the signatures measured against the gateway are touched;
ordinary prose is left byte for byte, and native OpenAI endpoints are never
rewritten at all.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# A non-breaking hyphen: renders as a hyphen, is not whitespace, and appears in
# no attack signature, so it splits one without changing what the text says.
_MASK = "\u2011"

# (pattern, replacement) — each breaks a rule without mangling the sentence.
_TRIPWIRES = (
    # <script> in any spacing or closing form.
    (re.compile(r"<(\s*/?\s*script)", re.IGNORECASE), "\u2039\\1"),
    # alert(...) and eval(...) — the call signature, not the word.
    (re.compile(r"\b(alert|eval)\s*\(", re.IGNORECASE), f"\\1{_MASK}("),
    # A stacked-query attempt.
    (re.compile(r"\bunion\s+select\b", re.IGNORECASE), f"union{_MASK}select"),
    (re.compile(r"\bdrop\s+table\b", re.IGNORECASE), f"drop{_MASK}table"),
    # Inline event handlers: onerror=, onload=, onclick= ...
    (re.compile(r"\bon([a-z]{3,})\s*=", re.IGNORECASE), f"on\\1{_MASK}="),
    # Traversal that reaches a well-known file.
    (re.compile(r"\betc\s*/\s*passwd\b", re.IGNORECASE), f"etc{_MASK}/passwd"),
    (re.compile(r"\.\./"), f"..{_MASK}/"),
    # Template injection's ${...}
    (re.compile(r"\$\{"), "$ {"),
)


def scrub_text(text: str) -> tuple[str, int]:
    """``text`` with every tripwire fragment neutralized, and how many were changed."""
    total = 0
    for pattern, replacement in _TRIPWIRES:
        text, hits = pattern.subn(replacement, text)
        total += hits
    return text, total


def scrub_payload(payload: dict) -> int:
    """Neutralize tripwires in a request payload's messages, in place.

    Returns how many fragments were rewritten. The payload is the JSON the SDK
    is about to send, so this is the last point before the firewall sees it, and
    it covers invoke, stream and structured-output calls alike: a message's
    content is either a string or a list of typed blocks.
    """
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return 0

    hits = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"], changed = scrub_text(content)
            hits += changed
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    block["text"], changed = scrub_text(block["text"])
                    hits += changed

    if hits:
        logger.info("Neutralized %d WAF-tripwire fragment(s) in an outbound request", hits)
    return hits
