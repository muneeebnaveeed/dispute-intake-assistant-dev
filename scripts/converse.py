"""Live multi-turn check (not a test — calls the API): a scripted cardholder answers in order.

    docker compose run --rm app python scripts/converse.py
"""
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from intake.session import IntakeSession  # noqa: E402

ANSWERS = [
    "someone charged me 180 euros at a shop I've never heard of, I still have my card",
    "it was yesterday, the shop is called Vellmar Home",
    "yes it was my visa card, my bank is OTP here in Hungary",
    "no I haven't reported it lost, it's in my wallet. and nobody else uses my card",
]


def main() -> None:
    s = IntakeSession(filed_on=date.today().isoformat())
    for text in ANSWERS:
        print(f"\nCARDHOLDER: {text}")
        r = s.step(text)
        print(f"CLERK [{r.question_field}]: {r.question}" if r.question else "CLERK: (complete)")
        if r.complete:
            break
    final = s.result()
    print("\nregime:", final.regime, "| turns:", final.turns, "| complete:", final.complete)
    print("missing:", final.missing_fields)
    print("flags:", [(f.code, f.severity, f.evidence) for f in final.flags])
    print(final.case_file.model_dump_json(indent=2, exclude={"narrative"}))


if __name__ == "__main__":
    main()
