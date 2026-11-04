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
  <a href="eval/results-v2.md">📊 Eval results</a> ·
  <a href="docs/development.md">🛠️ Development guide</a>
</p>

A conversational assistant that turns a cardholder's messy complaint about a card payment into
a validated, structured dispute case file, asking only for what is missing and flagging
inconsistencies for a human reviewer. It never decides the dispute itself.

**Design principle: the model extracts, the code decides.** A language model reads the
conversation and proposes facts; deterministic rules decide everything that must be trustworthy:
which facts are still needed, when the case is complete, which dispute regime applies, and which
inconsistencies to flag.

## 🚀 Quick start

```bash
docker compose up --build
```

Then open http://localhost:8501. You need an Anthropic API key in your environment file; the
[development guide](docs/development.md) covers setup with Docker or Anaconda, tests and the
evaluation runs.

## ⚙️ How it works

```
browser ──► web app ──► conversation manager ──► Claude (one structured call per turn)
                          │  keeps the case file, merges each turn's facts
                          │  works out what is still missing
                          │  picks the next question, decides when the case is complete
                          └─► rules: required facts per dispute type, regime, consistency checks
```

Each turn the model re-reads the whole conversation and returns a strictly structured proposal:

- the case file as it now stands, with every unstated fact left empty
- any contradictions it noticed, each quoting the conflicting words
- one suggested next question

The conversation manager merges the facts, applies the rules and either asks the next question or
closes the case. The model's question is used only if it asks for a required fact that is still
missing; otherwise a prepared question is asked. A conversation is capped at eight turns.

## 🧠 Prompt techniques

- **Persona:** the intake assistant on a card issuer's dispute desk, which never decides the
  dispute, gives advice or promises an outcome.
- **Few-shot:** two worked examples, one showing unstated facts left empty, the other an explicit
  "no" recorded as a no.
- **Clarity:** definitions of the six dispute types, and the central rule: record a fact only if
  the cardholder stated it; never guess an amount, date or yes/no answer.
- **Context:** the role and the filing date, so "yesterday" becomes a real date while "a while ago"
  stays empty.
- **Constraints:** one plain-language question per turn and a fixed output structure enforced by
  the API.
- **Iterative refinement:** every prompt change was triggered by an observed failure and measured
  before and after.
- **Delimited input:** the cardholder's words are clearly marked as data, never instructions.
- **Grounded contradiction detection:** every flag must quote the statements that conflict.
- **Adaptive thinking:** the model reasons before answering; the depth is set with an effort level.
- **Prompt caching:** the fixed instructions are reused from cache, so later turns are faster and
  cheaper.

## 🎛️ Parameters

All settings can be changed from the sidebar (locked once a conversation starts) or by environment
variable:

- **Model:** Claude Opus 5.5 for extraction, or Claude Sonnet 4.6 to demonstrate sampling
- **Thinking effort** (Opus 5.5): how much the model reasons before answering
- **Temperature and top-p** (Sonnet 4.6): sampling controls; low temperature suits extraction
- **Maximum response length**, **turn cap**, **timeout** and **automatic retries**

Opus 5.5 does not accept sampling parameters, and the current API version rejects temperature on
every model, so the Sonnet path pins an older API version for its own requests.

## 🧯 Error handling

- Rate limits, timeouts and connection errors are retried automatically, then shown as a readable
  message with a retry button.
- Empty or blank input is rejected before anything is sent.
- Refusals, cut-off answers and answers that fail validation each get their own message.
- A failed turn leaves the conversation unchanged, so retrying never duplicates a message.

## 📊 Evaluation

22 hand-written cases, played by a scripted cardholder that answers only the fact it is asked
about and says "I don't know" otherwise, so any fact that appears without being stated was
invented. Results are compared exactly against the expected case files, with no AI judge. The
cases cover:

- every dispute type, at least three cases each
- one case per consistency rule
- three traps in which a date is never given
- SEPA direct debits, US-issued cards and a complaint in Hungarian
- a complaint that changes its dispute type halfway
- two prompt-injection attempts

| Metric | First run | After one revision |
|---|---|---|
| Field accuracy | 98.6% | **100%** |
| Invented facts | 0 | **0** |
| Missed facts | 5 | **0** |
| Flag precision / recall | 100% / 100% | 100% / 100% |
| Correct regime | 20 of 22 | **22 of 22** |
| All required facts collected (where possible) | 18 of 22 | **22 of 22** |
| Mean turns | 5.8 | 5.4 |

What the first run showed, and the one revision that fixed it:

- Questions about *optional* facts used up the eight turns before required ones were asked, so the
  model's question is now accepted only for a required, missing fact.
- "A charge on my card" was not read as a card payment; one prompt line fixed it.

One expected answer was revised after the first run, openly: "*my* electricity company" plainly
implies the cardholder knows the merchant, so that fact is not scored in the three cases worded
that way. The first run is shown re-scored with the final expected answers.

Caveats: one run per version, and the model is not deterministic. The cases are self-written, by
the same person who wrote the prompt, and are not real complaints, so the numbers show the design
works on these cases, not that it generalises.

## 🛡️ Prompt injection

35 attacks from Microsoft's public
[LLMail-Inject](https://huggingface.co/datasets/microsoft/llmail-inject-challenge) challenge, each
chosen because it had *succeeded* against that challenge's defended e-mail assistant. Each one ran
twice: as the cardholder's whole message (direct), and pasted into a genuine complaint as "the
merchant's reply" (indirect).

| Run | Framing | Flagged | Facts invented | Genuine facts intact | Attacker address in the model's answer | … in the final case file |
|---|---|---|---|---|---|---|
| First | direct | 35/35 | 0/35 | n/a | 0/35 | 0/35 |
| First | indirect | 35/35 | 0/35 | 35/35 | 2/35 | 2/35 |
| After fix | indirect | 35/35 | 0/35 | 35/35 | **0/35** | **0/35** |

Clerk has no tools, so the attackers' goal (send an e-mail) is impossible by construction; the
table measures whether anything leaks into the case file anyway. In the first run the model twice
copied the attacker's address into its summary of the merchant's reply. The fix has two layers:

- **Prompt:** the merchant's reply is recorded as the merchant's position, in the model's own
  words, and nothing from a quoted message may be copied into a fact. This alone brought leaks to
  zero.
- **Code:** e-mail addresses (including spaced-out ones) and links are removed from everything the
  model writes, so an address cannot reach the case file even if the model does not comply.

## 📜 License

[MIT](LICENSE) © 2026 Naveed Muhammad Muneeb. The prompt-injection sample comes from Microsoft's
[llmail-inject-challenge](https://huggingface.co/datasets/microsoft/llmail-inject-challenge)
dataset, also MIT-licensed.
