"""Hard inconsistency rules: deterministic checks a reviewer can trust.

The model may add *semantic* flags (with a quote as evidence); these never depend on it.
Rules compare with `is True` on purpose: None means "not said" and must not trigger anything.
"""
from .schema import CaseFile, Flag


def hard_flags(case: CaseFile, filed_on: str) -> list[Flag]:
    t, h, flags = case.transaction, case.cardholder, []
    # ISO dates (enforced by the schema) compare correctly as strings.
    if t.date and t.date > filed_on:
        flags.append(Flag(code="DATE_ORDER", severity="high",
                          evidence=f"transaction {t.date} is after filing {filed_on}"))
    if h.card_in_possession is True and h.card_reported_lost_or_stolen is True:
        flags.append(Flag(code="POSSESSION_CONFLICT", severity="high",
                          evidence="card in possession but reported lost/stolen"))
    if case.dispute_type == "unauthorized" and h.authorized_third_party is True:
        flags.append(Flag(code="AUTHORIZED_USER", severity="high",
                          evidence="claims unauthorized but authorized a third party"))
    if case.dispute_type == "unauthorized" and h.recognizes_merchant is True:
        flags.append(Flag(code="KNOWN_MERCHANT", severity="low",
                          evidence="claims unauthorized but recognizes the merchant"))
    return flags
