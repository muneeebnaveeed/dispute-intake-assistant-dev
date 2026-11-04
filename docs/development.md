# Development guide

## Setup

Two equivalent ways; both use the same `environment.yml`. Either way, first create `.env` from
the example and put your Anthropic API key in it:

```bash
cp .env.example .env            # then set ANTHROPIC_API_KEY in .env
```

**Docker (nothing to install but Docker):**

```bash
docker compose up --build       # http://localhost:8501
docker compose run --rm app pytest
```

**Anaconda / Miniconda:**

```bash
conda env create -f environment.yml
conda activate dispute-intake
streamlit run app.py            # http://localhost:8501
pytest
```

On Linux hosts where a VPN blocks Docker's bridge network, run containers with host networking:

```bash
docker run --rm --network host --env-file .env -v "$PWD":/app <image> pytest -q
```

## Live checks (these call the API)

```bash
python scripts/smoke.py [--sampling]       # one complaint, 7 field checks
python scripts/converse.py                 # scripted 4-turn conversation
python -m eval.run --label v2              # 22-case evaluation (~120 calls)
python -m eval.rescore v1                  # re-score a saved run, no API calls
python -m eval.injection.run_llmail        # LLMail-Inject replay (~70 calls)
```

## Report

```bash
./scripts/build_report.sh                  # docs/report.md → docs/report.pdf (pandoc + Chrome)
```

## Layout

```
intake/           the library
  schema.py       data models; required fields per dispute type
  prompt.py       the system prompt and the cardholder-message wrappers
  extract.py      the only module that calls the API
  session.py      state and decisions: merge, completeness, question choice, flags
  regime.py       dispute regime (EU card, US card, SEPA direct debit)
  rules.py        hard consistency rules
  config.py       every tunable, overridable by environment variable
app.py            Streamlit interface
eval/             22 cases, scripted cardholder, scorer, runner, results
eval/injection/   LLMail-Inject sample, replay harness, results
scripts/          live checks, report build
tests/            pytest, no network
docs/             report, demo scripts, design decisions
```

## Results files

- Evaluation: `eval/results-v1.md` (raw first run), `eval/results-v1-rescored.md` (first run with
  the final labels), `eval/results-v2.md`; JSON next to each, with full transcripts.
- Prompt injection: `eval/injection/llmail_results.md` (first run, both framings),
  `eval/injection/llmail_results_v2.md` (after the fix, indirect framing).
- Design decisions and negative results: `docs/decisions.md`.
