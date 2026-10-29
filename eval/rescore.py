"""Re-score a saved run against the current labels and scorer, with no API calls.

    python -m eval.rescore v1        # reads results-v1.json, writes results-v1-rescored.md

Used when labels or the scorer change after a run, so the before/after comparison measures
only the prompt/code change. Flags are kept from the saved run: they don't depend on labels.
"""
import json
import sys
from pathlib import Path

from eval.run import render
from eval.score import aggregate, score_case
from eval.scripted_cardholder import load_cases
from intake.regime import select_regime
from intake.schema import REQUIRED_FIELDS, CaseFile, Flag, get_path
from intake.session import FinalCase

HERE = Path(__file__).parent


def main(label: str) -> None:
    saved = json.loads((HERE / f"results-{label}.json").read_text())
    cases = {c["id"]: c for c in load_cases()}
    scores = []
    for old in saved["cases"]:
        cf = CaseFile.model_validate(old["actual"])
        missing = (["dispute_type"] if cf.dispute_type is None else
                   [p for p in REQUIRED_FIELDS[cf.dispute_type] if get_path(cf, p) is None])
        case = cases[old["id"]]
        # Rebuild the scored flags from the saved counts: tp are expected codes, fp unknown codes.
        flags = [Flag(code=c, severity="high", evidence="") for c in case["expected"]["flags"]][
            : old["flag_tp"]] + [Flag(code="POSSESSION_CONFLICT", severity="high", evidence="")] * old["flag_fp"]
        final = FinalCase(case_file=cf, regime=select_regime(cf), missing_fields=missing,
                          flags=flags, turns=old["turns"], complete=not missing)
        s = score_case(case, final, old["error"])
        s["flag_tp"], s["flag_fp"], s["flag_fn"] = old["flag_tp"], old["flag_fp"], old["flag_fn"]
        scores.append(s)
    agg = aggregate(scores)
    report = render(f"{label} (re-scored with current labels)", saved["effort"], agg, scores)
    (HERE / f"results-{label}-rescored.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main(sys.argv[1])
