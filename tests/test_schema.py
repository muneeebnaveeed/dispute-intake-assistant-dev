"""Schema contract: every later task relies on these shapes."""
import pytest
from pydantic import ValidationError

from intake.schema import (
    DISPUTE_TYPES,
    REQUIRED_FIELDS,
    CaseFile,
    ExtractionResult,
    Flag,
    NextQuestion,
    Transaction,
    empty_case_file,
    get_path,
)


def test_empty_case_file_validates():
    case = empty_case_file()
    assert CaseFile.model_validate(case.model_dump()) == case


def test_empty_case_file_keeps_narrative():
    assert empty_case_file("I was charged twice").narrative == "I was charged twice"


def test_empty_case_file_has_no_dispute_type():
    assert empty_case_file().dispute_type is None


def test_every_dispute_type_has_required_fields():
    assert set(REQUIRED_FIELDS) == set(DISPUTE_TYPES)


@pytest.mark.parametrize("dispute_type", DISPUTE_TYPES)
def test_required_paths_resolve_to_none(dispute_type):
    case = empty_case_file()
    for path in REQUIRED_FIELDS[dispute_type]:
        assert get_path(case, path) is None, path


def test_get_path_unknown_field_raises():
    with pytest.raises(AttributeError):
        get_path(empty_case_file(), "transaction.nope")


@pytest.mark.parametrize("amount", [0, -5, 1_000_001])
def test_amount_out_of_range_rejected(amount):
    with pytest.raises(ValidationError):
        Transaction(amount=amount)


def test_amount_in_range_accepted():
    assert Transaction(amount=180.0).amount == 180.0


@pytest.mark.parametrize("currency", ["EU", "EURO"])
def test_currency_must_be_three_letters(currency):
    with pytest.raises(ValidationError):
        Transaction(currency=currency)


def test_date_must_be_iso():
    with pytest.raises(ValidationError):
        Transaction(date="12/09/2026")


def test_issuer_country_must_be_two_letters():
    with pytest.raises(ValidationError):
        Transaction(issuer_country="HUN")


def test_payment_method_enum():
    with pytest.raises(ValidationError):
        Transaction(payment_method="cash")


def test_dispute_type_enum():
    with pytest.raises(ValidationError):
        CaseFile(dispute_type="fraud")


def test_flag_severity_enum():
    with pytest.raises(ValidationError):
        Flag(code="X", severity="medium", evidence="")


def test_nested_defaults_not_shared():
    a, b = empty_case_file(), empty_case_file()
    a.transaction.amount = 10.0
    a.cardholder.contacted_merchant = True
    assert b.transaction.amount is None
    assert b.cardholder.contacted_merchant is None


def test_extraction_result_round_trips():
    result = ExtractionResult(
        case_file=CaseFile(dispute_type="duplicate_charge",
                           transaction=Transaction(amount=42.5, currency="EUR")),
        semantic_flags=[Flag(code="AMOUNT_MISMATCH", severity="low", evidence="'about 40'")],
        next_question=NextQuestion(field="transaction.date", text="When was the charge?"),
    )
    assert ExtractionResult.model_validate_json(result.model_dump_json()) == result
