"""Live smoke check (not a test — it calls the API and costs a few cents).

    docker compose run --rm app python scripts/smoke.py [--sampling]

Sends one complaint and checks the fields the plan expects. Run twice in a row to see the
system prompt served from the cache (cache_read_input_tokens > 0) on the second run.
"""
import argparse
import sys
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from intake.config import SamplingParams  # noqa: E402
from intake.extract import _default_client, extract_turn  # noqa: E402
from intake.prompt import first_turn  # noqa: E402

COMPLAINT = "someone charged me 180 euros at a shop I've never heard of, I still have my card"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sampling", action="store_true", help="use the Sonnet 4.6 path at T=0")
    args = ap.parse_args()

    # Wrap the client to capture usage without changing extract_turn's return type.
    client = _default_client()
    usage = {}
    for messages in (client.beta.messages, client.messages):
        original = messages.parse

        def spy(*a, _orig=original, **kw):
            res = _orig(*a, **kw)
            usage.update(model=res.model, stop=res.stop_reason, **res.usage.model_dump(
                include={"input_tokens", "output_tokens", "cache_read_input_tokens",
                         "cache_creation_input_tokens"}))
            return res

        messages.parse = spy

    sampling = SamplingParams(temperature=0.0) if args.sampling else None
    t0 = time.monotonic()
    out = extract_turn([first_turn(COMPLAINT, date.today().isoformat())], sampling=sampling)
    print(f"{time.monotonic() - t0:.1f}s", usage)
    print(out.model_dump_json(indent=2))

    t, h = out.case_file.transaction, out.case_file.cardholder
    checks = {
        "dispute_type == unauthorized": out.case_file.dispute_type == "unauthorized",
        "amount == 180": t.amount == 180,
        "currency == EUR": t.currency == "EUR",
        "recognizes_merchant is False": h.recognizes_merchant is False,
        "card_in_possession is True": h.card_in_possession is True,
        "date is None": t.date is None,
        "next_question asks date or merchant": bool(out.next_question) and
            out.next_question.field in {"transaction.date", "transaction.merchant_name"},
    }
    for name, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + name)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
