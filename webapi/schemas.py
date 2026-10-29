"""Request payload accepted by ``POST /api/runs``.

Every field except ``ticker`` and ``analysis_date`` is optional: a value left
out keeps whatever DEFAULT_CONFIG resolved from the environment (``.env``), so
the same defaults the CLI reads apply here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    analysis_date: str = Field(min_length=1, max_length=16)
    asset_type: str = "stock"
    analysts: list[str] = Field(default_factory=lambda: ["market", "social", "news", "fundamentals"])
    quick_think_llm: str | None = None
    deep_think_llm: str | None = None
    max_debate_rounds: int | None = Field(default=None, ge=1, le=10)
    max_risk_rounds: int | None = Field(default=None, ge=1, le=10)
    output_language: str | None = None
    checkpoint_enabled: bool = False
