# Dispute Intake Assistant — Project Report

*Introduction to Generative AI, University of Debrecen, Fall 2026. Solo project.*
*Skeleton created 2026-09-10; sections are filled as the corresponding tasks land. Design
rationale is kept in `decisions.md` and cited here rather than repeated.*

## 1. Problem and motivation
<!-- Why intake is where disputes go wrong; first-party fraud context; what a good case file
     buys downstream. Cite decisions.md D1–D3. -->

## 2. Related concepts
<!-- Structured output / constrained decoding; extraction vs. generation; hallucination and
     abstention; chain of thought and built-in thinking; prompt caching; LLM-as-extractor with
     code-as-judge. -->

## 3. Architecture
<!-- Diagram; the turn sequence; why completeness, regime, and rules live in code. D4, D7. -->

## 4. Prompt design
<!-- The null rule; one question per turn; the worked example and example leakage; the
     cardholder_message tag; what changed between v1 and v2 and why. -->

## 5. Evaluation
<!-- Case design (20 cases, spread); metrics; results v1 and v2 tables; error analysis of every
     miss; run-to-run spread. D8. -->

## 6. Security — prompt injection
<!-- Threat model; the ten mitigations and which are implemented; the two adversarial cases and
     what happened. D9. -->

## 7. Limitations and ethics
<!-- Single-model dependence; no PII handling; in-memory sessions; the model only proposes;
     distribution shift of self-written cases; what a real issuer would need. -->

## 8. Future work
<!-- In-band reasoning field experiment; multilingual; human review UI; audit log. -->

## 9. References
