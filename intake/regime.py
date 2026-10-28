"""Which dispute regime applies — decided in code, never by the model.

Labels are this project's own simplification, not legal advice.
"""
from typing import Literal

from .schema import CaseFile

Regime = Literal["EU_SEPA_DIRECT_DEBIT", "EU_CARD", "US_CARD", "UNDETERMINED"]

_EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE",
       "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}


def select_regime(case: CaseFile) -> Regime:
    t = case.transaction
    if t.payment_method == "sepa_direct_debit":
        return "EU_SEPA_DIRECT_DEBIT"
    if t.payment_method == "card" and t.issuer_country in _EU:
        return "EU_CARD"
    if t.payment_method == "card" and t.issuer_country == "US":
        return "US_CARD"
    return "UNDETERMINED"
