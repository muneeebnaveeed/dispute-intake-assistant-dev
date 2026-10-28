import pytest

from intake.regime import select_regime
from intake.schema import CaseFile, Transaction


def _case(**txn) -> CaseFile:
    return CaseFile(transaction=Transaction(**txn))


def test_sepa_direct_debit_wins_regardless_of_country():
    assert select_regime(_case(payment_method="sepa_direct_debit", issuer_country="US")) \
        == "EU_SEPA_DIRECT_DEBIT"


@pytest.mark.parametrize("country", ["HU", "DE", "FR"])
def test_eu_card(country):
    assert select_regime(_case(payment_method="card", issuer_country=country)) == "EU_CARD"


def test_us_card():
    assert select_regime(_case(payment_method="card", issuer_country="US")) == "US_CARD"


@pytest.mark.parametrize("txn", [
    {},                                                   # nothing known yet
    {"payment_method": "card"},                           # country missing
    {"issuer_country": "HU"},                             # method missing
    {"payment_method": "card", "issuer_country": "GB"},   # outside the modelled regimes
])
def test_undetermined(txn):
    assert select_regime(_case(**txn)) == "UNDETERMINED"
