<h1 align="center">🗂️ Clerk</h1>

<p align="center"><b>A dispute intake assistant.</b><br>
The model extracts, the code decides.</p>

<p align="center">
  <img alt="Python 3.10" src="https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="Claude Opus 5.5" src="https://img.shields.io/badge/Claude-Opus%205.5-D97757?logo=anthropic&logoColor=white">
  <img alt="Pydantic v2" src="https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow"></a>
</p>
<p align="center">
  <img alt="Tests: 177 passed" src="https://img.shields.io/badge/tests-177%20passed-2EA44F?logo=pytest&logoColor=white">
  <img alt="Eval: 100% field accuracy" src="https://img.shields.io/badge/eval-100%25%20field%20accuracy-2EA44F">
  <img alt="Invented facts: 0" src="https://img.shields.io/badge/invented%20facts-0-2EA44F">
  <img alt="Prompt injection: 35/35 flagged" src="https://img.shields.io/badge/LLMail--Inject-35%2F35%20flagged-6F42C1">
</p>

<p align="center">
  <a href="docs/report.pdf">📄 Report (PDF)</a> ·
  <a href="docs/demo.md">🎬 Demo scripts</a> ·
  <a href="docs/decisions.md">🧭 Design decisions</a> ·
  <a href="eval/results-v2.md">📊 Eval results</a>
</p>

A conversational assistant that turns a cardholder's messy complaint about a card transaction
into a validated, structured dispute case file, asking only for what is missing and flagging
inconsistencies for a human reviewer.

**Design principle: the model extracts, the code decides.** One LLM call per turn does
extraction only, into a schema where every field is optional and unstated things stay `null`.
Deterministic Python owns completeness, regime selection, and the hard inconsistency rules.

Course project for *Introduction to Generative AI* (University of Debrecen, Fall 2026). Solo.

## 🚀 Run it

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

## ⚙️ How it works

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

## 📊 Evaluation results

22 hand-written cases (3+ per dispute type, one per hard rule, three invention traps where a
date is never given, SEPA, US-issued, Hungarian, a self-correcting case, two injections), played
by a scripted cardholder that answers only the field it is asked about and says "I don't know"
otherwise. Scored exactly against the labels; no judge model. Opus 5.5, effort `medium`.

| Metric | v1 | v2 |
|---|---|---|
| Field accuracy | 98.6% | **100%** |
| Invented values (filled but never stated) | 0 | **0** |
| Missed values | 5 | **0** |
| Flag precision / recall | 100% / 100% | 100% / 100% |
| Regime correct | 20/22 | **22/22** |
| Required fields all collected (where possible) | 18/22 | **22/22** |
| Mean turns | 5.8 | 5.4 |

v1 is shown re-scored with the final labels (`eval/results-v1-rescored.md`; raw run in
`results-v1.md`). Reading every v1 miss gave one revision: (1) questions about *optional* fields
were using up the 8-turn cap before required ones, so the session now accepts the model's question
only for a required, still-missing field; (2) "a charge on my card" now states the payment method.
One label was revised after v1, openly: "*my* electricity company" plainly implies the cardholder
recognises the merchant, so that field is not scored in the three cases phrased that way.

Caveats: one run per version and the model is not deterministic; 22 self-written cases are not
real complaints, and they were written by the same person who wrote the prompt. The numbers show
the design works on these cases, not that it generalises.

## 🛡️ Prompt-injection results

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

Clerk has no tools, so the attackers' goal (send an email) is impossible by construction; the
table measures whether anything leaks into the case file anyway. In v1 the two leaks were in
`cardholder.merchant_response`, where the model summarised the quoted reply including the
attacker's request. v2 adds two layers. **Prompt:** `merchant_response` is defined as the
merchant's position in the model's own words, and nothing from a quoted message may be copied
into a field; this alone took raw leaks to 0/35. **Code:** the session strips email addresses
(including spaced-out ones like `contact @ contact . com`) and links from every model-written
free-text field and caps their length, so an address cannot reach the case file even when the
model does not comply. One run per version; the model is not deterministic, so 0/35 is evidence,
not proof; the code layer is the guarantee. Reports: `eval/injection/llmail_results.md` (v1),
`llmail_results_v2.md` (v2).

## 🧪 Live checks (call the API)

```bash
python scripts/smoke.py [--sampling]       # one complaint, 7 field checks
python scripts/converse.py                 # scripted 4-turn conversation
python -m eval.injection.run_llmail        # LLMail-Inject replay (~70 calls)
python -m eval.run --label v2              # 22-case eval (~120 calls)
```

Inside Docker on Linux use host networking, e.g.
`docker run --rm --network host --env-file .env -v "$PWD":/app <image> python scripts/smoke.py`.

## 🗂️ Layout

```
intake/     extraction, schema, rules, regime, session: the library
app.py      Streamlit demo
eval/       20-case scripted evaluation + scoring; injection/ = LLMail-Inject replay
scripts/    live smoke checks
tests/      pytest, no network
docs/       report, demo scripts, slides
```

## 📜 License

[MIT](LICENSE) © 2026 Naveed Muhammad Muneeb. The LLMail-Inject sample in `eval/injection/` comes from
Microsoft's [llmail-inject-challenge](https://huggingface.co/datasets/microsoft/llmail-inject-challenge)
dataset, also MIT-licensed.
