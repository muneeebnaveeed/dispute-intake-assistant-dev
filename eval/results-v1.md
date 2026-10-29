# Eval results — v1

22 cases · `claude-opus-5-5` · effort `medium` · scripted cardholder answers by field, "I don't know" otherwise.

| Metric | Value |
|---|---|
| Field accuracy (mean per case) | 98.3% |
| **Invented values** (filled but never stated) | **1** in 1 case(s) |
| Missed values (stated but left empty) | 5 |
| Wrong values | 0 |
| Flag precision / recall (hard rules + injection) | 100.0% / 100.0% |
| Regime correct | 20/22 |
| Completion as expected | 19/22 |
| Mean turns | 5.8 |
| Errors | 0 |

| Case | Accuracy | Invented | Missed | Wrong | Flags tp/fp/fn | Regime | Complete | Turns |
|---|---|---|---|---|---|---|---|---|
| case-01 | 93.8% | — | cardholder.card_reported_lost_or_stolen | — | 0/0/0 | ✓ | ✓ | 8 |
| case-02 | 100.0% | — | — | — | 1/0/0 | ✓ | ✓ | 7 |
| case-03 | 87.5% | — | cardholder.card_reported_lost_or_stolen, transaction.payment_method | — | 1/0/0 | ✗ UNDETERMINED | ✓ | 8 |
| case-04 | 93.8% | — | cardholder.card_reported_lost_or_stolen | — | 1/0/0 | ✓ | ✓ | 8 |
| case-05 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 7 |
| case-06 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 5 |
| case-07 | 100.0% | — | — | — | 0/0/0 | ✓ | ✗ | 8 |
| case-08 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 5 |
| case-09 | 93.8% | cardholder.recognizes_merchant | — | — | 0/0/0 | ✓ | ✓ | 3 |
| case-10 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 4 |
| case-11 | 100.0% | — | — | — | 0/0/0 | ✓ | ✗ | 8 |
| case-12 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 4 |
| case-13 | 100.0% | — | — | — | 1/0/0 | ✓ | ✓ | 5 |
| case-14 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 4 |
| case-15 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 4 |
| case-16 | 100.0% | — | — | — | 0/0/0 | ✓ | ✗ | 8 |
| case-17 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 5 |
| case-18 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 5 |
| case-19 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 5 |
| case-20 | 100.0% | — | — | — | 0/0/0 | ✓ | ✓ | 5 |
| case-21 | 100.0% | — | — | — | 1/0/0 | ✓ | ✓ | 4 |
| case-22 | 93.3% | — | transaction.payment_method | — | 1/0/0 | ✗ UNDETERMINED | ✓ | 8 |
