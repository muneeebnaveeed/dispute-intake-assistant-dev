"""extract_turn against a fake client: request shape and error mapping, no network."""
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest

from intake.config import SamplingParams
from intake.extract import IntakeError, extract_turn
from intake.schema import ExtractionResult, empty_case_file

HISTORY = [{"role": "user", "content": "<cardholder_message>\nhi\n</cardholder_message>"}]
OK = ExtractionResult(case_file=empty_case_file())
_REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


class FakeMessages:
    def __init__(self, result=None, error=None):
        self.result = result or SimpleNamespace(stop_reason="end_turn", parsed_output=OK)
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def fake_client(**kw):
    stable, beta = FakeMessages(**kw), FakeMessages(**kw)
    return SimpleNamespace(messages=stable, beta=SimpleNamespace(messages=beta)), stable, beta


def _status_error(cls, code):
    return cls("boom", response=httpx.Response(code, request=_REQ), body=None)


# --- request shape -------------------------------------------------------------------------

def test_extract_path_uses_opus_with_effort_and_no_sampling():
    client, stable, beta = fake_client()
    assert extract_turn(HISTORY, client=client) == OK
    assert stable.calls == []
    call = beta.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_format"] is ExtractionResult
    assert call["output_config"] == {"effort": "medium"}
    assert call["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in call["betas"]
    assert "thinking" not in call  # Opus 5.5 always thinks; disabling it is a 400
    for p in ("temperature", "top_p", "top_k", "extra_body"):
        assert p not in call


def test_system_prompt_is_cached():
    client, _, beta = fake_client()
    extract_turn(HISTORY, client=client)
    (block,) = beta.calls[0]["system"]
    assert block["cache_control"] == {"type": "ephemeral"}


def test_sampling_path_uses_sonnet_and_never_sends_thinking():
    client, stable, beta = fake_client()
    extract_turn(HISTORY, client=client, sampling=SamplingParams(temperature=0.7, top_k=40))
    assert beta.calls == []
    call = stable.calls[0]
    assert call["model"] == "claude-sonnet-4-6"
    assert "thinking" not in call
    assert call["extra_body"] == {"temperature": 0.7, "top_k": 40}  # unset top_p not sent
    # The SDK's default API version rejects sampling parameters outright.
    assert call["extra_headers"] == {"anthropic-version": "2023-06-01"}


def test_effort_and_max_tokens_are_parameters():
    client, _, beta = fake_client()
    extract_turn(HISTORY, client=client, effort="high", max_tokens=2000)
    assert beta.calls[0]["output_config"] == {"effort": "high"}
    assert beta.calls[0]["max_tokens"] == 2000


# --- error mapping -------------------------------------------------------------------------

@pytest.mark.parametrize("error, kind", [
    (_status_error(anthropic.RateLimitError, 429), "rate_limit"),
    (anthropic.APITimeoutError(request=_REQ), "timeout"),
    (anthropic.APIConnectionError(request=_REQ), "connection"),
    (_status_error(anthropic.AuthenticationError, 401), "auth"),
    (_status_error(anthropic.InternalServerError, 500), "api"),
])
def test_api_errors_become_intake_errors(error, kind):
    client, _, _ = fake_client(error=error)
    with pytest.raises(IntakeError) as exc:
        extract_turn(HISTORY, client=client)
    assert exc.value.kind == kind
    assert exc.value.message  # shown to the user verbatim, so never empty


def test_schema_violation_is_unparseable():
    from pydantic import ValidationError
    try:
        ExtractionResult.model_validate({"case_file": {"transaction": {"amount": -1}}})
    except ValidationError as e:
        err = e
    client, _, _ = fake_client(error=err)
    with pytest.raises(IntakeError) as exc:
        extract_turn(HISTORY, client=client)
    assert exc.value.kind == "unparseable"


@pytest.mark.parametrize("result, kind", [
    (SimpleNamespace(stop_reason="refusal", parsed_output=None), "refusal"),
    (SimpleNamespace(stop_reason="max_tokens", parsed_output=None), "truncated"),
    (SimpleNamespace(stop_reason="end_turn", parsed_output=None), "unparseable"),
])
def test_bad_responses_become_intake_errors(result, kind):
    client, _, _ = fake_client(result=result)
    with pytest.raises(IntakeError) as exc:
        extract_turn(HISTORY, client=client)
    assert exc.value.kind == kind


def test_empty_history_is_rejected_before_any_call():
    client, stable, beta = fake_client()
    with pytest.raises(IntakeError) as exc:
        extract_turn([], client=client)
    assert exc.value.kind == "empty_input"
    assert stable.calls == beta.calls == []
