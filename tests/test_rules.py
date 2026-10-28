from intake.rules import hard_flags
from intake.schema import CaseFile, Cardholder, Transaction

FILED_ON = "2026-10-28"


def _codes(case: CaseFile) -> list[str]:
    return [f.code for f in hard_flags(case, FILED_ON)]


def _severity(case: CaseFile, code: str) -> str:
    return next(f.severity for f in hard_flags(case, FILED_ON) if f.code == code)


def test_clean_case_has_no_flags():
    case = CaseFile(
        dispute_type="unauthorized",
        transaction=Transaction(merchant_name="Shop", amount=180.0, currency="EUR",
                                date="2026-10-20", payment_method="card", issuer_country="HU"),
        cardholder=Cardholder(recognizes_merchant=False, card_in_possession=True,
                              card_reported_lost_or_stolen=False, authorized_third_party=False),
    )
    assert hard_flags(case, FILED_ON) == []


def test_empty_case_has_no_flags():
    assert hard_flags(CaseFile(), FILED_ON) == []


def test_transaction_after_filing_date():
    case = CaseFile(transaction=Transaction(date="2026-11-02"))
    assert _codes(case) == ["DATE_ORDER"]
    assert _severity(case, "DATE_ORDER") == "high"


def test_transaction_on_filing_date_is_fine():
    assert _codes(CaseFile(transaction=Transaction(date=FILED_ON))) == []


def test_possession_conflict():
    case = CaseFile(cardholder=Cardholder(card_in_possession=True,
                                          card_reported_lost_or_stolen=True))
    assert _codes(case) == ["POSSESSION_CONFLICT"]
    assert _severity(case, "POSSESSION_CONFLICT") == "high"


def test_authorized_user_on_unauthorized_claim():
    case = CaseFile(dispute_type="unauthorized",
                    cardholder=Cardholder(authorized_third_party=True))
    assert _codes(case) == ["AUTHORIZED_USER"]
    assert _severity(case, "AUTHORIZED_USER") == "high"


def test_known_merchant_on_unauthorized_claim_is_low():
    case = CaseFile(dispute_type="unauthorized",
                    cardholder=Cardholder(recognizes_merchant=True))
    assert _codes(case) == ["KNOWN_MERCHANT"]
    assert _severity(case, "KNOWN_MERCHANT") == "low"


def test_unauthorized_rules_only_fire_for_unauthorized():
    case = CaseFile(dispute_type="duplicate_charge",
                    cardholder=Cardholder(recognizes_merchant=True, authorized_third_party=True))
    assert _codes(case) == []


def test_unknown_fields_never_trigger_rules():
    # None means "not said" — it must not count as True or False.
    case = CaseFile(dispute_type="unauthorized",
                    cardholder=Cardholder(card_in_possession=True))
    assert _codes(case) == []


def test_flags_accumulate():
    case = CaseFile(
        dispute_type="unauthorized",
        transaction=Transaction(date="2026-12-01"),
        cardholder=Cardholder(card_in_possession=True, card_reported_lost_or_stolen=True,
                              authorized_third_party=True, recognizes_merchant=True),
    )
    assert _codes(case) == ["DATE_ORDER", "POSSESSION_CONFLICT", "AUTHORIZED_USER",
                            "KNOWN_MERCHANT"]
