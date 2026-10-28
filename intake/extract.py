"""The only module that calls the model: one structured extraction per conversation turn.

The model proposes a case file; nothing here decides anything. Every failure, from a rate
limit to output that fails validation, comes back as an IntakeError the UI can show as-is.
"""
from functools import lru_cache

import anthropic
from anthropic.types import MessageParam
from pydantic import ValidationError

from . import config
from .config import Effort, SamplingParams
from .prompt import SYSTEM_PROMPT
from .schema import ExtractionResult

# Server-side refusal fallback: if the safety classifiers decline a turn, the API re-runs it
# on a fallback model inside the same call instead of returning an empty refusal.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_SAMPLING_API_VERSION = "2023-06-01"

_SYSTEM = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]


class IntakeError(Exception):
    """A failure the user should see. `kind` is for code, `message` is for people."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


@lru_cache(maxsize=1)
def _default_client() -> anthropic.Anthropic:
    # Built on first use, not at import, so tests and the UI load without an API key.
    # The SDK retries rate limits, timeouts and connection errors with backoff before
    # anything below sees them.
    return anthropic.Anthropic(timeout=config.TIMEOUT_S, max_retries=config.MAX_RETRIES)


def extract_turn(
    history: list[MessageParam],
    *,
    sampling: SamplingParams | None = None,
    effort: Effort = config.EFFORT,
    max_tokens: int = config.MAX_TOKENS,
    client: anthropic.Anthropic | None = None,
) -> ExtractionResult:
    """Extract the case file from the whole conversation so far.

    sampling=None  → MODEL_EXTRACT (Opus 5.5): adaptive thinking, depth set by `effort`.
    sampling=…     → MODEL_SAMPLING (Sonnet 4.6): temperature/top_p/top_k, no thinking.
    Same prompt, same schema; only the model and its knobs differ.
    """
    if not history:
        raise IntakeError("empty_input", "There is nothing to read yet. Please describe the problem.")
    client = client or _default_client()

    try:
        if sampling is None:
            res = client.beta.messages.parse(
                model=config.MODEL_EXTRACT,
                max_tokens=max_tokens,
                system=_SYSTEM,
                messages=history,
                output_format=ExtractionResult,
                output_config={"effort": effort},
                betas=[_FALLBACK_BETA],
                fallbacks="default",
            )
        else:
            res = client.messages.parse(
                model=config.MODEL_SAMPLING,
                max_tokens=max_tokens,
                system=_SYSTEM,
                messages=history,
                output_format=ExtractionResult,
                # API version 2026-10-21 (the SDK's default) removed temperature/top_p/top_k on
                # every model, and SDK 2.x dropped the typed arguments. The 2023-06-01 version
                # still accepts them on Sonnet 4.6, so this path alone pins it.
                extra_headers={"anthropic-version": _SAMPLING_API_VERSION},
                extra_body=sampling.model_dump(exclude_none=True),
            )
    # Most specific first: APITimeoutError is a subclass of APIConnectionError.
    except anthropic.RateLimitError as e:
        raise IntakeError("rate_limit", "The service is busy (rate limited). Wait a moment and send again.") from e
    except anthropic.APITimeoutError as e:
        raise IntakeError("timeout", "The model took too long to answer. Please send your message again.") from e
    except anthropic.APIConnectionError as e:
        raise IntakeError("connection", "Could not reach the model. Check the internet connection and retry.") from e
    except anthropic.AuthenticationError as e:
        raise IntakeError("auth", "The API key was rejected. Check ANTHROPIC_API_KEY in .env.") from e
    except anthropic.APIStatusError as e:
        raise IntakeError("api", f"The model service returned an error ({e.status_code}). Please retry.") from e
    except ValidationError as e:
        # Range/pattern constraints are checked client-side, after generation (see schema.py).
        raise IntakeError("unparseable", "The model's answer did not pass validation. Please rephrase or retry.") from e

    if res.stop_reason == "refusal":
        raise IntakeError("refusal", "The model declined to process this message.")
    if res.stop_reason == "max_tokens":
        raise IntakeError("truncated", "The model's answer was cut off. Raise max_tokens and retry.")
    if res.parsed_output is None:
        raise IntakeError("unparseable", "The model's answer could not be read. Please retry.")
    return res.parsed_output
