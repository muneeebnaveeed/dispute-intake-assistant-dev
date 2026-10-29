"""The eval set checks itself: labels must agree with the code's own regime and rules, and the
scripted cardholder must route answers by field. No network."""
import pytest

from eval.scripted_cardholder import DONT_KNOW, load_cases, run_case
from intake.regime import select_regime
from intake.rules import hard_flags
from intake.schema import (
    DISPUTE_TYPES, REQUIRED_FIELDS, CaseFile, ExtractionResult, NextQuestion,
)
from intake.session import FIELD_WHITELIST

CASES = load_cases()


def expected_case_file(case: dict) -> CaseFile:
    """Build the CaseFile the labels describe ("*" → a placeholder string, "?" → skipped)."""
    tree: dict = {}
    for path, value in case["expected"]["case_file"].items():
        if value == "?":
            continue
        if value == "*":
            value = "placeholder"
        node = tree
        *parents, leaf = path.split(".")
        for p in parents:
            node = node.setdefault(p, {})
        node[leaf] = value
    return CaseFile.model_validate(tree)


def test_case_set_shape():
    assert len(CASES) == 22
    assert len({c["id"] for c in CASES}) == len(CASES)
    types = [c["expected"]["case_file"]["dispute_type"] for c in CASES]
    for t in DISPUTE_TYPES:
        assert types.count(t) >= 3, t
    assert sum("INSTRUCTION_IN_INPUT" in c["expected"]["flags"] for c in CASES) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_labels_use_real_fields(case):
    for path in case["expected"]["case_file"]:
        assert path in FIELD_WHITELIST, path
    for path in case["answers"]:
        assert path in FIELD_WHITELIST, path


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_labels_agree_with_regime_and_hard_rules(case):
    cf = expected_case_file(case)
    assert select_regime(cf) == case["expected"]["regime"]
    hard = [f.code for f in hard_flags(cf, case["filed_on"])]
    labelled = [c for c in case["expected"]["flags"] if c != "INSTRUCTION_IN_INPUT"]
    assert hard == labelled


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_complete_label_matches_required_fields(case):
    cf = expected_case_file(case)
    required = REQUIRED_FIELDS[cf.dispute_type]
    stated = set(case["expected"]["case_file"])
    assert case["expected"]["complete"] == (set(required) <= stated)


# --- the scripted cardholder ---------------------------------------------------------------------

class AskInOrder:
    """Fake extractor: asks for the given fields in order, records what it was told."""

    def __init__(self, *fields):
        self.fields = list(fields)
        self.heard = []

    def __call__(self, history, **_):
        self.heard.append(history[-1]["content"])
        f = self.fields.pop(0) if self.fields else "transaction.amount"
        # A known type, so the asked fields count as required-and-missing.
        return ExtractionResult(case_file=CaseFile(dispute_type="duplicate_charge"),
                                next_question=NextQuestion(field=f, text="?"))


CASE = {"id": "t", "filed_on": "2026-10-28", "opening": "hello",
        "answers": {"transaction.date": "on the 3rd"}, "expected": {}}


def test_answers_are_routed_by_field_and_unknowns_get_dont_know():
    fake = AskInOrder("transaction.date", "transaction.currency")
    run = run_case({**CASE}, extract=fake)
    assert "on the 3rd" in fake.heard[1]
    assert DONT_KNOW in fake.heard[2]
    assert run.final.turns == 8  # nothing ever fills in, so the turn cap ends it


def test_first_reply_is_sent_once_regardless_of_field():
    fake = AskInOrder("transaction.currency", "transaction.date")
    run_case({**CASE, "first_reply": "actually it was a subscription"}, extract=fake)
    assert "actually it was a subscription" in fake.heard[1]
    assert "on the 3rd" in fake.heard[2]
