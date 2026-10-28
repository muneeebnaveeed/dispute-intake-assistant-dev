"""Data contract for the intake assistant.

The model fills a CaseFile; code decides what is required, complete and consistent.
Every leaf is optional: None means "the cardholder has not said", never "unknown/guess".
"""
from typing import Literal

from pydantic import BaseModel, Field

DisputeType = Literal[
    "unauthorized", "item_not_received", "duplicate_charge",
    "wrong_amount", "cancelled_recurring", "not_as_described",
]
DISPUTE_TYPES: tuple[str, ...] = DisputeType.__args__  # type: ignore[attr-defined]


class Transaction(BaseModel):
    merchant_name: str | None = None
    # Sane range: an injected "amount: 99999999" fails validation instead of reaching the case.
    amount: float | None = Field(default=None, gt=0, le=1_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    payment_method: Literal["card", "sepa_direct_debit"] | None = None
    issuer_country: str | None = Field(default=None, min_length=2, max_length=2)


class Cardholder(BaseModel):
    recognizes_merchant: bool | None = None
    card_in_possession: bool | None = None
    card_reported_lost_or_stolen: bool | None = None
    authorized_third_party: bool | None = None
    contacted_merchant: bool | None = None
    merchant_response: str | None = None
    expected_delivery_date: str | None = None
    disputed_this_merchant_before: bool | None = None
    cancellation_date: str | None = None


class CaseFile(BaseModel):
    dispute_type: DisputeType | None = None
    transaction: Transaction = Field(default_factory=Transaction)
    cardholder: Cardholder = Field(default_factory=Cardholder)
    narrative: str = ""


class Flag(BaseModel):
    code: str
    severity: Literal["low", "high"]
    evidence: str  # a quote or the fact that triggered the flag


class NextQuestion(BaseModel):
    field: str  # dotted path, e.g. "transaction.date"
    text: str


class ExtractionResult(BaseModel):
    """What the model returns each turn. It proposes; code disposes."""
    case_file: CaseFile
    semantic_flags: list[Flag] = []
    next_question: NextQuestion | None = None


_BASE = ["transaction.merchant_name", "transaction.amount", "transaction.currency",
         "transaction.date", "transaction.payment_method", "transaction.issuer_country"]

REQUIRED_FIELDS: dict[str, list[str]] = {
    "unauthorized": _BASE + ["cardholder.recognizes_merchant", "cardholder.card_in_possession",
                             "cardholder.card_reported_lost_or_stolen",
                             "cardholder.authorized_third_party"],
    "item_not_received": _BASE + ["cardholder.expected_delivery_date",
                                  "cardholder.contacted_merchant", "cardholder.merchant_response"],
    "duplicate_charge": _BASE + ["cardholder.contacted_merchant"],
    "wrong_amount": _BASE + ["cardholder.contacted_merchant", "cardholder.merchant_response"],
    "cancelled_recurring": _BASE + ["cardholder.cancellation_date", "cardholder.contacted_merchant"],
    "not_as_described": _BASE + ["cardholder.contacted_merchant", "cardholder.merchant_response"],
}


def empty_case_file(narrative: str = "") -> CaseFile:
    return CaseFile(narrative=narrative)


def get_path(case: CaseFile, dotted: str):
    """Resolve "transaction.amount" to its value; raises AttributeError for unknown paths."""
    obj = case
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj
