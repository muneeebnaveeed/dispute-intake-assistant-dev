"""Every tunable in one place, each overridable from the environment (or the Streamlit sidebar).

Two models, deliberately (decisions D11):
- MODEL_EXTRACT does every extraction that reaches the case file. Claude Opus 5.5 always
  thinks and rejects temperature/top_p/top_k; depth is tuned with EFFORT instead.
- MODEL_SAMPLING is used only where sampling control is the point (the temperature demo).
  Claude Sonnet 4.6 is the newest model that still accepts temperature/top_p/top_k.
"""
import os
from typing import Literal

from pydantic import BaseModel, Field

Effort = Literal["low", "medium", "high", "xhigh", "max"]

MODEL_EXTRACT: str = os.getenv("MODEL_EXTRACT", "claude-opus-5-5")
MODEL_SAMPLING: str = os.getenv("MODEL_SAMPLING", "claude-sonnet-4-6")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "16000"))
EFFORT: Effort = os.getenv("EFFORT", "medium")  # type: ignore[assignment]  # Opus 5.5's default
TURN_CAP: int = int(os.getenv("TURN_CAP", "8"))
TIMEOUT_S: float = float(os.getenv("TIMEOUT_S", "90"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))


class SamplingParams(BaseModel):
    """Sampling controls for MODEL_SAMPLING. Unset fields are not sent at all."""
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    top_p: float | None = Field(default=None, gt=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1)
