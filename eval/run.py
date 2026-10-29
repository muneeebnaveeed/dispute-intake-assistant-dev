"""Run the eval set against the real model and write a report (calls the API).

    docker run --rm --network host --env-file .env -v "$PWD":/app <image> \
        python -m eval.run --label v1 [--cases case-01 case-17] [--workers 4] [--effort medium]

Writes eval/results-<label>.json (scores + transcripts) and eval/results-<label>.md.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from eval.score import aggregate, score_case  # noqa: E402
from eval.scripted_cardholder import load_cases, run_case  # noqa: E402
from intake import config  # noqa: E402

HERE = Path(__file__).parent


def render(label: str, effort: str, agg: dict, scores: list[dict]) -> str:
    pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    lines = [
        f"# Eval results — {label}", "",
        f"{agg['cases']} cases · `{config.MODEL_EXTRACT}` · effort `{effort}` · "
        f"scripted cardholder answers by field, \"I don't know\" otherwise.", "",
        "| Metric | Value |", "|---|---|",
        f"| Field accuracy (mean per case) | {pct(agg['field_accuracy'])} |",
        f"| **Invented values** (filled but never stated) | **{agg['invented_total']}** "
        f"in {agg['cases_with_invention']} case(s) |",
        f"| Missed values (stated but left empty) | {agg['missed_total']} |",
        f"| Wrong values | {agg['wrong_total']} |",
        f"| Flag precision / recall (hard rules + injection) | {pct(agg['flag_precision'])} / "
        f"{pct(agg['flag_recall'])} |",
        f"| Regime correct | {agg['regime_matches']}/{agg['cases']} |",
        f"| Completion as expected | {agg['complete_matches']}/{agg['cases']} |",
        f"| Mean turns | {agg['mean_turns']:.1f} |",
        f"| Errors | {agg['errors']} |", "",
        "| Case | Accuracy | Invented | Missed | Wrong | Flags tp/fp/fn | Regime | Complete | Turns |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in scores:
        lines.append(
            f"| {s['id']}{' ⚠ ' + s['error'] if s['error'] else ''} | {pct(s['field_accuracy'])} "
            f"| {', '.join(s['invented']) or '—'} | {', '.join(s['missed']) or '—'} "
            f"| {', '.join(s['wrong']) or '—'} | {s['flag_tp']}/{s['flag_fp']}/{s['flag_fn']} "
            f"| {'✓' if s['regime_match'] else '✗ ' + s['regime']} "
            f"| {'✓' if s['complete_match'] else '✗'} | {s['turns']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--effort", default=config.EFFORT)
    args = ap.parse_args()

    cases = load_cases(args.cases)

    def one(case):
        run = run_case(case, effort=args.effort)
        s = score_case(case, run.final, run.error)
        s["transcript"] = run.transcript
        s["actual"] = run.final.case_file.model_dump(exclude={"narrative"})
        return s

    with ThreadPoolExecutor(args.workers) as pool:
        scores = list(pool.map(one, cases))
    agg = aggregate(scores)
    (HERE / f"results-{args.label}.json").write_text(
        json.dumps({"label": args.label, "effort": args.effort, "aggregate": agg,
                    "cases": scores}, indent=2, ensure_ascii=False))
    report = render(args.label, args.effort, agg, scores)
    (HERE / f"results-{args.label}.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
