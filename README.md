# Dispute Intake Assistant

A conversational assistant that turns a cardholder's messy complaint about a card transaction
into a validated, structured dispute case file — asking only for what is missing and flagging
inconsistencies for a human reviewer.

**Design principle: the model extracts, the code decides.** One LLM call per turn does
extraction only, into a schema where every field is optional and unstated things stay `null`.
Deterministic Python owns completeness, regime selection, and the hard inconsistency rules.

Course project for *Introduction to Generative AI* (University of Debrecen, Fall 2026). Solo.

## Run it

Two equivalent ways; both use the same `environment.yml`.

**Docker (nothing to install but Docker):**

```bash
cp .env.example .env            # then put your ANTHROPIC_API_KEY in .env
docker compose up --build       # http://localhost:8501
docker compose run --rm app pytest
```

**Anaconda / Miniconda:**

```bash
conda env create -f environment.yml
conda activate dispute-intake
cp .env.example .env            # then put your ANTHROPIC_API_KEY in .env
streamlit run app.py            # http://localhost:8501
pytest
```

## Layout

```
intake/     extraction, schema, rules, regime, session — the library
app.py      Streamlit demo
eval/       20-case scripted evaluation + scoring
tests/      pytest, no network
docs/       report, demo scripts, slides
```
