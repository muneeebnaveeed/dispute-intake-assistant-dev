from eval.score import aggregate, score_case
from intake.schema import CaseFile, Cardholder, Flag, Transaction
from intake.session import FIELD_WHITELIST, FinalCase

CASE = {
    "id": "case-x", "filed_on": "2026-10-28",
    "expected": {
        "case_file": {"dispute_type": "wrong_amount", "transaction.merchant_name": "Café Morro",
                      "transaction.amount": 54, "transaction.currency": "EUR",
                      "cardholder.contacted_merchant": True, "cardholder.merchant_response": "*",
                      "cardholder.disputed_this_merchant_before": "?"},
        "regime": "UNDETERMINED", "flags": ["DATE_ORDER"], "complete": False,
    },
}


def final(cf: CaseFile, flags=(), regime="UNDETERMINED", turns=3, missing=("transaction.date",),
          complete=False) -> FinalCase:
    return FinalCase(case_file=cf, regime=regime, missing_fields=list(missing), flags=list(flags),
                     turns=turns, complete=complete)


PERFECT = CaseFile(
    dispute_type="wrong_amount",
    transaction=Transaction(merchant_name="  café morro ", amount=54.0, currency="EUR"),
    cardholder=Cardholder(contacted_merchant=True, merchant_response="They'll look into it",
                          disputed_this_merchant_before=True),  # "?" → not scored
)


def test_perfect_case():
    s = score_case(CASE, final(PERFECT, [Flag(code="DATE_ORDER", severity="high", evidence="")]))
    assert s["field_accuracy"] == 1.0
    assert s["scored_fields"] == len(FIELD_WHITELIST) - 1  # one "?" field skipped
    assert s["invented"] == [] and s["missed"] == [] and s["wrong"] == []
    assert (s["flag_tp"], s["flag_fp"], s["flag_fn"]) == (1, 0, 0)
    assert s["regime_match"] and s["complete_match"]


def test_invented_missed_wrong_and_flags():
    cf = CaseFile(
        dispute_type="wrong_amount",
        transaction=Transaction(merchant_name="Cafe Morro", amount=45.0, currency=None,
                                date="2026-10-26"),               # wrong, wrong, missed, invented
        cardholder=Cardholder(contacted_merchant=True, merchant_response=None),  # "*" missed
    )
    flags = [Flag(code="POSSESSION_CONFLICT", severity="high", evidence=""),   # false positive
             Flag(code="AMOUNT_CHANGED", severity="low", evidence="")]         # semantic: ignored
    s = score_case(CASE, final(cf, flags, regime="EU_CARD", missing=()))
    assert s["invented"] == ["transaction.date"]
    assert sorted(s["missed"]) == ["cardholder.merchant_response", "transaction.currency"]
    assert sorted(s["wrong"]) == ["transaction.amount", "transaction.merchant_name"]
    assert (s["flag_tp"], s["flag_fp"], s["flag_fn"]) == (0, 1, 1)
    assert not s["regime_match"] and not s["complete_match"]
    assert s["field_accuracy"] == (s["scored_fields"] - 5) / s["scored_fields"]


def test_trailing_full_stop_and_case_are_ignored_in_strings():
    case = {**CASE, "expected": {**CASE["expected"],
                                 "case_file": {"transaction.merchant_name": "Zöldkert Kft."}}}
    cf = CaseFile(transaction=Transaction(merchant_name="zöldkert kft"))
    assert "transaction.merchant_name" not in score_case(case, final(cf))["wrong"]


def test_error_is_reported():
    s = score_case(CASE, final(CaseFile()), error="timeout")
    assert s["error"] == "timeout"


def test_aggregate():
    a = score_case(CASE, final(PERFECT, [Flag(code="DATE_ORDER", severity="high", evidence="")]))
    b = score_case(CASE, final(CaseFile(transaction=Transaction(date="2026-10-01"))))
    agg = aggregate([a, b])
    assert agg["cases"] == 2
    assert agg["cases_with_invention"] == 1 and agg["invented_total"] == 1
    assert agg["flag_precision"] == 1.0 and agg["flag_recall"] == 0.5
    assert 0 < agg["field_accuracy"] < 1


def test_turn_cap_completion_is_not_label_completion():
    # Session ended by the turn cap with fields still missing: matches complete=False labels.
    s = score_case(CASE, final(CaseFile(), missing=("transaction.date",), complete=True))
    assert s["complete_match"] is True
