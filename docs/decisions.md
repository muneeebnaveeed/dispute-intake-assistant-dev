# Design decisions

A running record of the choices behind this project: what was considered, what was picked,
and why. Written as decisions are made, so the final report can cite them rather than
reconstruct them. Each entry lists the options in the order they were weighed, with the chosen
one marked **→ chosen**.

Status key: *decided* (fixed), *provisional* (revisit if evidence says so), *open*.

---

## D1. What to build — *decided 2026-09-10*

The goal: a project that *uses* generative AI, on any topic. Selection criteria:
(1) Gen AI is the core, not decoration; (2) buildable in about eight evenings alongside a
bachelor's thesis; (3) doubles as portfolio evidence in payments/fintech; (4) has a live demo
that fits a ten-minute slot.

| Option | Verdict |
|---|---|
| **Dispute intake assistant** — turn a cardholder's messy complaint into a structured dispute case file, asking only for what is missing | **→ chosen.** Exercises extraction, structured output, multi-turn state, and hallucination control, all measurable. Domain I know from work. |
| Evidence-based adjudication copilot — RAG over dispute-regime rules producing a cited recommendation for a human | Honourable mention. Stronger reasoning story, but needs a realistic synthetic case corpus before anything can be built or evaluated — a week of work on its own. |
| Regime-aware customer-communication generator — templated dispute letters per regime with an LLM-as-judge compliance check | Honourable mention. Smallest scope; weaker demo (text generation looks like every other LLM demo). |
| RAG Q&A over a personal Markdown knowledge base | Independent of the domain; strong "built a core generative-AI pattern" story; weaker portfolio link. |
| Lab-report generator from raw experiment notes | Fallback only. |
| Image/audio generation, fine-tuning projects | Ruled out: no career overlap; fine-tuning too expensive for the timeline and unnecessary for the behaviour needed. |

**Name — *decided 2026-10-28*: Clerk.** It names the role the assistant plays: it takes the
complaint down, asks for what is missing, and hands the file to a human reviewer. It does not
decide the dispute. Considered: *Casefile* (names the output, not the role), *Intake* (too
generic), *Chargeback Clerk* ("chargeback" is narrower than "dispute"), *Nothing Invented*
(good slide line for the zero-invention metric, too long for a name).

## D2. Domain: card disputes vs. insurance claims — *decided 2026-09-10*

The same architecture works for any structured-intake domain. An **insurance first-notice-of-loss
(FNOL) assistant** was drafted in full for one afternoon — claim lines instead of dispute types,
coverage section instead of regime, fraud indicators such as a claim filed days after policy
start. It was dropped the same day.

- **→ Card disputes.** The domain I work in, so the questionnaire, dispute types, and
  inconsistency rules come from real knowledge rather than guesses, and the deliverable still
  stands alone.
- Insurance FNOL. Would have removed any question of overlap with my thesis, but the
  independence is achieved another way (see D3), and the domain knowledge would have been
  thinner.

## D3. Relationship to my thesis — *decided 2026-09-10*

My bachelor's thesis is an issuer-side automated dispute-resolution engine (Go, PostgreSQL). This
project borrows **only the domain idea**. Considered:

- Share the questionnaire JSON schema so the thesis could consume this project's output over
  HTTP later. Rejected: even a shared contract couples the two and muddies "whose work is
  this" in grading.
- **→ Fully independent.** Own repository, own schema, own regime labels, no imports, no
  endpoints. Output is a JSON file. If the thesis ever wants it, that is a future adapter, not
  a dependency.

## D4. Architecture: where the intelligence lives — *decided 2026-09-10*

The central principle: **the model extracts, the code decides.**

| Option | Verdict |
|---|---|
| Let the model run the whole conversation and decide when the case is complete | Rejected. Completeness, regime, and hard rules would then be unverifiable and non-reproducible. |
| Agent with tools (`ask_question`, `set_field`, `mark_complete`) | Considered. Cleaner-looking, but every decision would still be the model's, and the loop is harder to evaluate deterministically. |
| **→ One extraction call per turn, schema-constrained, every field nullable; deterministic Python owns completeness, regime selection, hard inconsistency rules, and the turn cap** | Chosen. The model proposes (fields, one next question, semantic contradictions with quoted evidence); code disposes. Every trust-critical decision is a pure function with a unit test. |

Consequences: the model is stateless — the session object is the state; the "null rule"
(never fill what wasn't stated) becomes the headline metric; prompt injection can mislabel but
cannot act (see D9).

## D5. Model and API features — *provisional 2026-09-10, model updated 2026-10-28*

> **Update 2026-10-28:** the extraction model is now **Claude Opus 5.5** (`claude-opus-5-5`),
> the successor to Opus 5 at a lower price. Two differences matter here: thinking cannot be
> disabled at all (effort is the only control), and effort defaults to `medium`, not `high`,
> so `intake/config.py` sets it explicitly. Requests also opt into the server-side refusal
> fallback (`fallbacks="default"`, beta `server-side-fallback-2026-07-01`): if a safety
> classifier declines a turn, the API re-runs it on a fallback model within the same call.
> The smoke check passes 7/7 at `medium`; the eval decides whether `high` earns its cost.


- **→ Claude Opus 5** via the official Anthropic Python SDK. Anthropic's recommended default;
  the whole evaluation run costs well under two euros, so cost is not a reason to trade
  capability.
- Structured outputs (`messages.parse` with a Pydantic model) rather than "please answer in
  JSON" — constrained decoding guarantees shape; the prompt and eval handle truth.
- Adaptive thinking is on by default on this model; reasoning depth is tuned with `effort`,
  not with "think step by step" in the prompt.
- Prompt caching on the frozen system prompt.
- Not used: sampling controls (unavailable on current models — outputs are non-deterministic,
  so the eval is run twice and the spread reported); refusal fallback (optional hardening,
  noted in limitations).

## D6. Language and environment — *decided 2026-09-10*

| Option | Verdict |
|---|---|
| TypeScript on Node (my strongest stack) | Drafted first — full plan written, then dropped. |
| **→ Python 3.10** | Chosen because the Python SDK + Pydantic + Streamlit is the most direct path. 3.10 is the SDK's floor. |
| Environment: local Anaconda install | Not installed on my machine; system Python is 3.9. |
| Environment: `uv` / plain venv | Fast, but conda is more familiar to most readers. |
| **→ Conda environment (`environment.yml`) running inside Docker** | The same file works for anyone with Anaconda (`conda env create -f environment.yml`) and for anyone with only Docker (`docker compose up`). conda-forge only: Anaconda's default channels now require accepting Terms of Service, which broke a non-interactive build. |

## D7. Demo surface — *decided 2026-09-10*

| Option | Verdict |
|---|---|
| Terminal chat (CLI) | Drafted first. Cheapest, but hard for an audience to follow. |
| Custom web UI (Express + static page, later Streamlit) | A web demo was required. |
| **→ Streamlit** | Chosen. One Python file, chat pane plus a live case-file panel that re-renders every turn (type, regime, missing fields shrinking, flags appearing). The standard Python demo format. Sessions are in memory — acceptable for a demo, stated in limitations. |

## D8. Evaluation design — *decided 2026-09-10*

- **→ Golden set of 20 hand-written cases**, driven by a scripted cardholder that answers the
  assistant's follow-up questions by field. Metrics: field-level accuracy, **invention rate**
  (fields filled that the cardholder never stated — the hallucination measure), flag
  precision/recall, regime match, turns to completion.
- Scoring is deterministic code, **not an LLM judge**: outputs are structured and can be
  compared exactly, so a judge model would add cost and a second source of error.
- One prompt revision between run v1 and run v2, both kept. The point is measurement, not a
  perfect score; cases are never edited to improve numbers.
- Known limitation: self-written cases are not real complaints (distribution shift).

## D9. Prompt-injection posture — *decided 2026-09-10*

Cardholder text is untrusted input inside the prompt. Defence in depth: instructions only in
the system block; user text wrapped in a `<cardholder_message>` tag and declared as data;
schema-constrained output (no free-text channel); all decisions in code; the model's own output
validated (field whitelist, enum/date/range checks, question text capped and rendered as plain
text); narrative set by code from raw text; an `INSTRUCTION_IN_INPUT` flag so attempts are
visible; no tools, so no side effects; two adversarial cases in the eval. Full list and
mapping to code in the project plan; results in the report's Security section.

## D10. Things deliberately left out — *decided 2026-09-10*

- **RAG** — no external knowledge needed; regime selection is a lookup table.
- **Fine-tuning** — no training data; prompting plus a schema already reaches the behaviour.
- **Multi-model cascades / cheaper models** — one model, one cache namespace, simpler story.
  (A second model *is* used, but only for the sampling demonstration, never as a cascade — D11.)
- **Persistence, auth, audit log** — a real issuer would need them; out of scope for a demo.

## D11. A second model for sampling parameters — *decided 2026-09-17, revised 2026-10-28*

Visible parameterisation such as temperature was a goal. Opus 5.5 rejects temperature,
top_p and top_k, so the extraction path cannot show them.

| Option | Verdict |
|---|---|
| Show only `max_tokens` and `effort` on Opus 5.5 | Honest, but temperature is the parameter people know. |
| **→ Add a sampling path on Claude Sonnet 4.6** | Chosen. Same prompt, same schema, same `messages.parse`; only the model and the sampling fields differ. Sonnet 4.6 is the newest generation that still accepts sampling parameters. No thinking on this path: extended thinking constrains sampling. |
| Move all extraction to Sonnet 4.6 | Rejected: trades capability on every turn for a knob that extraction does not want (low temperature is the right setting for extraction anyway). |

**Finding, 2026-10-28.** The SDK (2.3.0) sends API version `2026-10-21`, and on that version
the API rejects `temperature` on *every* model ("Extra inputs are not permitted"), including
Sonnet 4.6, Opus 4.6 and Haiku 4.5. The SDK has also dropped the typed arguments. Sending
`anthropic-version: 2023-06-01` restores them, and structured outputs still work there. So the
sampling path alone pins that header and passes the values through `extra_body`; the
extraction path stays on the current version. Sampling controls are being retired from the
platform; this project demonstrates them on the last version that accepts them.

Caches are model-scoped and thinking blocks do not transfer between models, so a conversation
never switches model part-way through.

## D12. Dates: the filing date travels in the first message — *decided 2026-10-28*

Cardholders say "yesterday" or "on the 3rd". Resolving that needs today's date, but a date in
the system prompt would change the cached prefix every day. The filing date therefore goes in
a `<filing_date>` tag at the start of the first user message, which never changes during a
conversation, so caching still works (the smoke run reads 4,197 cached tokens on the second
call). The prompt allows resolving a date that the cardholder pins to one day; vague
references ("last week") stay null. The hard `DATE_ORDER` rule uses the same filing date.

---

## Open questions
- ~~Does an in-band `reasoning` field placed first in the schema (a manual chain-of-thought
  variant) improve extraction accuracy?~~ *Tried 2026-10-29 and reverted:* with a required
  `reasoning` field first in `ExtractionResult`, Opus 5.5 returned `stop_reason: "refusal"` on
  the plain smoke-test complaint, and the server-side fallback did not recover it. Without the
  field the same request passes 7/7. Most likely cause: Opus 5.5's safety classifiers decline
  requests that look like extracting its reasoning. Chain of thought stays in its built-in form,
  adaptive thinking tuned by `effort`; a summarised view of it (`display: "summarized"`) is the
  supported way to make it visible.
- Does an English system prompt extract correctly from Hungarian text with no changes?
  *One eval case tests this.*
