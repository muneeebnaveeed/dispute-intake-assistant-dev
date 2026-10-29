"""A scripted cardholder: plays one eval case against a real IntakeSession, no UI.

Case format (eval/cases/case-NN.json):
  opening      the first message
  first_reply  optional: sent as the first follow-up whatever Clerk asks (used for the case
               that starts with the wrong dispute type and corrects itself)
  answers      {dotted field path: reply text}; Clerk's question is answered by its field
  expected     case_file: {dotted path: value} for every stated field. Anything not listed
                          must stay null — that is the invention test. "*" = must be filled,
                          any wording (free text); "?" = not scored.
               regime, flags (hard-rule codes and INSTRUCTION_IN_INPUT), complete

A question about a field the script has no answer for gets "I don't know", so a value that
appears there anyway was invented.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from intake.extract import IntakeError, extract_turn
from intake.session import FinalCase, IntakeSession

CASES_DIR = Path(__file__).parent / "cases"
DONT_KNOW = "I don't know."


@dataclass
class CaseRun:
    case_id: str
    final: FinalCase | None
    transcript: list[tuple[str, str]] = field(default_factory=list)  # (speaker, text)
    error: str | None = None


def load_cases(ids: list[str] | None = None) -> list[dict]:
    cases = [json.loads(p.read_text()) for p in sorted(CASES_DIR.glob("case-*.json"))]
    return [c for c in cases if not ids or c["id"] in ids]


def run_case(case: dict, extract=extract_turn, **extract_kwargs) -> CaseRun:
    session = IntakeSession(filed_on=case["filed_on"], extract=extract)
    run = CaseRun(case["id"], None)
    message = case["opening"]
    first_reply = case.get("first_reply")
    try:
        while True:
            run.transcript.append(("cardholder", message))
            step = session.step(message, **extract_kwargs)
            if step.complete:
                break
            run.transcript.append((f"clerk [{step.question_field}]", step.question))
            if first_reply:
                message, first_reply = first_reply, None
            else:
                message = case["answers"].get(step.question_field, DONT_KNOW)
    except IntakeError as e:
        run.error = e.kind
    run.final = session.result()
    return run
