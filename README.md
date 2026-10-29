# Clerk

**A dispute intake assistant.**

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

## How it works

```
browser ──► Streamlit (app.py) ──► IntakeSession (intake/session.py) ──► extract_turn ──► Claude
                                     │  merge known fields                (intake/extract.py)
                                     │  missing fields → complete?        one structured call
                                     │  question whitelist + fallback     per turn
                                     ├─ select_regime  (intake/regime.py)
                                     └─ hard_flags     (intake/rules.py)
```

Each turn the model re-reads the whole conversation and returns a schema-constrained
`ExtractionResult`: the case file so far, any contradictions it noticed (each quoting its
evidence), and one proposed next question. Everything that must be trustworthy is decided in
code, with unit tests: which fields a dispute type requires, whether the case is complete, which
regime applies, the hard inconsistency rules, and the 8-turn cap. The model's question is used
only if it targets a real, still-empty field.

**Prompt techniques** (`intake/prompt.py`), in the course's terms: **persona** (the intake
assistant on a card issuer's dispute desk); **few-shot** (two worked examples: one shows unstated
fields left null, the other an explicit "no" recorded as false); the **3C principle**: clarity
(the null rule and dispute-type definitions), context (role, dispute types, the filing date) and
constraints (one question per turn, dotted field paths, a JSON schema enforced by structured
output); and **iterative refinement**, measured before and after (see the injection results and
`docs/decisions.md`). Supporting techniques: delimiting untrusted input in `<cardholder_message>`
tags, grounded contradiction detection (every flag quotes its evidence), adaptive thinking tuned
by effort, and prompt caching of the frozen system prompt.

**Parameters** (`intake/config.py`, all overridable by environment variable and shown in the
sidebar): model, thinking effort (Opus 5.5), temperature and top_p (Sonnet 4.6 path), max_tokens,
turn cap, timeout, retries.

**Error handling**: rate limits, timeouts and connection errors are retried by the SDK, then
surface as a readable `IntakeError` with a retry button; blank input is rejected before any
call; refusals, truncated output and output that fails validation each have their own message.
A failed call leaves the conversation unchanged.

## Prompt-injection results

Replayed 35 attacks from Microsoft's [LLMail-Inject](https://huggingface.co/datasets/microsoft/llmail-inject-challenge)
challenge (MIT), chosen because each one *succeeded* against the challenge's defended email
assistant: it made the assistant send an email to `contact@contact.com` without being
detected. Each attack ran twice on Opus 5.5: as the cardholder's whole message (direct), and
pasted into a genuine duplicate-charge complaint as "the merchant's reply" (indirect).
Full report: [`eval/injection/llmail_results.md`](eval/injection/llmail_results.md).

| Run | Framing | Detected (`INSTRUCTION_IN_INPUT`) | Fields invented | Genuine facts intact | Attacker address in the model's proposal | …in the final case file |
|---|---|---|---|---|---|---|
| v1 | direct | 35/35 | 0/35 | n/a | 0/35 | 0/35 |
| v1 | indirect | 35/35 | 0/35 | 35/35 | 2/35 | 2/35 |
| v2 | indirect | 35/35 | 0/35 | 35/35 | 0/35 | 0/35 |

Clerk has no tools, so the attackers' goal — send an email — is impossible by construction; the
table measures whether anything leaks into the case file anyway. In v1 the two leaks were in
`cardholder.merchant_response`, where the model summarised the quoted reply including the
attacker's request. v2 adds two layers. **Prompt:** `merchant_response` is defined as the
merchant's position in the model's own words, and nothing from a quoted message may be copied
into a field; this alone took raw leaks to 0/35. **Code:** the session strips email addresses
(including spaced-out ones like `contact @ contact . com`) and links from every model-written
free-text field and caps their length, so an address cannot reach the case file even when the
model does not comply. One run per version; the model is not deterministic, so 0/35 is evidence,
not proof — the code layer is the guarantee. Reports: `eval/injection/llmail_results.md` (v1),
`llmail_results_v2.md` (v2).

## Live checks (call the API)

```bash
python scripts/smoke.py [--sampling]       # one complaint, 7 field checks
python scripts/converse.py                 # scripted 4-turn conversation
python -m eval.injection.run_llmail        # LLMail-Inject replay (~70 calls)
```

Inside Docker on Linux use host networking, e.g.
`docker run --rm --network host --env-file .env -v "$PWD":/app <image> python scripts/smoke.py`.

## Layout

```
intake/     extraction, schema, rules, regime, session — the library
app.py      Streamlit demo
eval/       20-case scripted evaluation + scoring; injection/ = LLMail-Inject replay
scripts/    live smoke checks
tests/      pytest, no network
docs/       report, demo scripts, slides
```
