"""Deterministic scoring: outputs are structured, so they are compared exactly. No judge model.

Per case, over every askable field (FIELD_WHITELIST):
  invented   expected null, actual filled   ← the headline metric (the null rule)
  missed     expected a value, actual null
  wrong      both filled, values differ
Strings compare case-insensitively, ignoring surrounding space and a trailing full stop;
numbers within 1e-6. "*" in the labels means "must be filled, any wording"; "?" is not scored.
Flags are scored only for codes code can predict: the hard rules and INSTRUCTION_IN_INPUT.
The model's own semantic flag codes are free-form and are reported, not scored.
"""
from intake.rules import hard_flags
from intake.schema import CaseFile, get_path
from intake.session import FIELD_WHITELIST, FinalCase

SCORED_FLAG_CODES = {f.code for f in hard_flags(  # every code rules.py can emit
    CaseFile.model_validate({"dispute_type": "unauthorized",
                             "transaction": {"date": "2999-01-01"},
                             "cardholder": {"card_in_possession": True,
                                            "card_reported_lost_or_stolen": True,
                                            "authorized_third_party": True,
                                            "recognizes_merchant": True}}),
    "2000-01-01")} | {"INSTRUCTION_IN_INPUT"}


def _norm(v):
    if isinstance(v, str):
        return v.strip().rstrip(".").strip().casefold()
    return v


def _equal(expected, actual) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected is actual
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(expected - actual) < 1e-6
    return _norm(expected) == _norm(actual)


def score_case(case: dict, final: FinalCase, error: str | None = None) -> dict:
    labels = case["expected"]["case_file"]
    invented, missed, wrong, scored = [], [], [], 0
    for path in sorted(FIELD_WHITELIST):
        expected = labels.get(path)
        if expected == "?":
            continue
        scored += 1
        actual = get_path(final.case_file, path)
        if expected is None:
            if actual is not None:
                invented.append(path)
        elif actual is None:
            missed.append(path)
        elif expected != "*" and not _equal(expected, actual):
            wrong.append(path)

    got = {f.code for f in final.flags} & SCORED_FLAG_CODES
    want = set(case["expected"]["flags"])
    return {
        "id": case["id"],
        "error": error,
        "scored_fields": scored,
        "field_accuracy": (scored - len(invented) - len(missed) - len(wrong)) / scored,
        "invented": invented, "missed": missed, "wrong": wrong,
        "flag_tp": len(got & want), "flag_fp": len(got - want), "flag_fn": len(want - got),
        "semantic_flags": sorted({f.code for f in final.flags} - SCORED_FLAG_CODES),
        "regime": final.regime, "regime_match": final.regime == case["expected"]["regime"],
        # "complete" in the labels means every required field filled. FinalCase.complete is also
        # true when the turn cap ends the session, so compare against missing_fields instead.
        "complete": not final.missing_fields,
        "complete_match": (not final.missing_fields) == case["expected"]["complete"],
        "turns": final.turns,
    }


def aggregate(scores: list[dict]) -> dict:
    n = len(scores)
    tp = sum(s["flag_tp"] for s in scores)
    fp = sum(s["flag_fp"] for s in scores)
    fn = sum(s["flag_fn"] for s in scores)
    return {
        "cases": n,
        "errors": sum(bool(s["error"]) for s in scores),
        "field_accuracy": sum(s["field_accuracy"] for s in scores) / n,
        "invented_total": sum(len(s["invented"]) for s in scores),
        "cases_with_invention": sum(bool(s["invented"]) for s in scores),
        "missed_total": sum(len(s["missed"]) for s in scores),
        "wrong_total": sum(len(s["wrong"]) for s in scores),
        "flag_precision": tp / (tp + fp) if tp + fp else 1.0,
        "flag_recall": tp / (tp + fn) if tp + fn else 1.0,
        "regime_matches": sum(s["regime_match"] for s in scores),
        "complete_matches": sum(s["complete_match"] for s in scores),
        "mean_turns": sum(s["turns"] for s in scores) / n,
    }
