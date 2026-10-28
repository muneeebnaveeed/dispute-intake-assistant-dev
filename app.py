"""Clerk — Streamlit demo: a cardholder chat on the left, the live case file on the right.

A thin UI: every decision lives in IntakeSession. Streamlit reruns this script on every
interaction, so the session object is kept in st.session_state.
"""
import json
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from intake import config
from intake.config import SamplingParams
from intake.extract import IntakeError
from intake.schema import REQUIRED_FIELDS, get_path
from intake.session import IntakeSession

load_dotenv()
st.set_page_config(page_title="Clerk — dispute intake", page_icon="🗂️", layout="wide")

GREETING = "Hello, I'm Clerk. Tell me what happened with the payment you want to dispute."
ERROR_ICONS = {"rate_limit": "⏳", "timeout": "⌛", "connection": "📡", "empty_input": "✏️"}
OPUS, SONNET = "Opus 5.5 — extraction (effort)", "Sonnet 4.6 — sampling (temperature)"


def new_case() -> None:
    st.session_state.session = IntakeSession(filed_on=date.today().isoformat())
    st.session_state.chat = [("assistant", GREETING)]
    st.session_state.error = None
    st.session_state.retry_text = None


if "session" not in st.session_state:
    new_case()
s: IntakeSession = st.session_state.session
started = s.turns > 0


# --- sidebar: visible parameterisation ---------------------------------------------------------

with st.sidebar:
    st.header("Clerk")
    st.caption("The model extracts. The code decides.")
    if st.button("New case", use_container_width=True, type="primary"):
        new_case()
        st.rerun()

    st.subheader("Model settings")
    st.caption("Locked once the conversation starts: caches are per model.")
    model = st.radio("Model", [OPUS, SONNET], disabled=started, key="model")
    if model == OPUS:
        effort = st.select_slider("Thinking effort", ["low", "medium", "high", "xhigh", "max"],
                                  value=config.EFFORT, disabled=started)
        extract_kwargs = {"effort": effort}
        st.caption(f"`{config.MODEL_EXTRACT}` always thinks; effort sets how much. "
                   "It does not accept temperature.")
    else:
        temperature = st.slider("temperature", 0.0, 1.0, 0.0, 0.1, disabled=started)
        use_top_p = st.checkbox("set top_p", disabled=started)
        top_p = st.slider("top_p", 0.05, 1.0, 0.9, 0.05, disabled=started or not use_top_p)
        sampling = SamplingParams(temperature=temperature, top_p=top_p if use_top_p else None)
        extract_kwargs = {"sampling": sampling}
        st.caption(f"`{config.MODEL_SAMPLING}`, thinking off. Low temperature suits "
                   "extraction: the same complaint should give the same case file.")

    with st.expander("Advanced"):
        extract_kwargs["max_tokens"] = st.number_input(
            "max_tokens", 1000, 64000, config.MAX_TOKENS, 1000, disabled=started)
        s.turn_cap = st.number_input("Turn cap", 1, 20, s.turn_cap, disabled=started)
        st.caption(f"Timeout {config.TIMEOUT_S:.0f}s, {config.MAX_RETRIES} automatic retries "
                   "on rate limits and connection errors.")


# --- one turn ----------------------------------------------------------------------------------

def send(text: str) -> None:
    st.session_state.error = None
    try:
        with st.spinner("Clerk is reading…"):
            step = s.step(text, **extract_kwargs)
    except IntakeError as e:
        st.session_state.error = e
        st.session_state.retry_text = text if e.kind != "empty_input" else None
        return
    st.session_state.retry_text = None
    st.session_state.chat.append(("user", text))
    st.session_state.chat.append(
        ("assistant", step.question or "Thank you, I have everything I need. "
                                       "A reviewer will look at your case."))


left, right = st.columns([5, 4], gap="large")

with left:
    st.subheader("Cardholder chat")
    for role, text in st.session_state.chat:
        with st.chat_message(role):
            st.text(text)  # plain text: model-written questions are never rendered as markdown

    err: IntakeError | None = st.session_state.error
    if err:
        st.error(f"{ERROR_ICONS.get(err.kind, '⚠️')} {err.message}")
        if st.session_state.retry_text and st.button("Retry last message"):
            send(st.session_state.retry_text)
            st.rerun()

    done = s.is_complete()
    if text := st.chat_input("Case complete — start a new case from the sidebar" if done
                             else "Describe the problem…", disabled=done):
        send(text)
        st.rerun()


# --- live case file ------------------------------------------------------------------------------

def show(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


with right:
    r = s.result()
    st.subheader("Live case file")
    st.markdown(f"**Dispute type** `{r.case_file.dispute_type or 'unknown'}` · "
                f"**Regime** `{r.regime}` · **Turns** {r.turns} / {s.turn_cap}")

    if r.case_file.dispute_type:
        required = REQUIRED_FIELDS[r.case_file.dispute_type]
        st.progress((len(required) - len(r.missing_fields)) / len(required),
                    text=f"{len(required) - len(r.missing_fields)} of {len(required)} required fields")
        rows = [{"": "✓" if get_path(r.case_file, p) is not None else "·",
                 "field": p.split(".")[-1].replace("_", " "),
                 "value": show(get_path(r.case_file, p))} for p in required]
        st.dataframe(rows, hide_index=True, use_container_width=True)

    if r.complete and r.missing_fields:
        st.warning(f"Turn cap reached with {len(r.missing_fields)} field(s) still missing.")
    elif r.complete:
        st.success("Case file complete")

    st.markdown("**Flags for the reviewer**")
    if not r.flags:
        st.caption("None so far.")
    for f in r.flags:
        box = st.error if f.severity == "high" else st.warning
        box(f"**{f.code}** ({f.severity})\n\n{f.evidence}")

    export = {"filed_on": s.filed_on, "regime": r.regime, "complete": r.complete,
              "missing_fields": r.missing_fields, "flags": [f.model_dump() for f in r.flags],
              "turns": r.turns, "case_file": r.case_file.model_dump()}
    st.download_button("Download case file (JSON)", json.dumps(export, indent=2),
                       file_name="case-file.json", mime="application/json",
                       disabled=not started, use_container_width=True)
    with st.expander("Raw JSON"):
        st.json(export)
    if s.last is not None:
        with st.expander("Model's last proposal (before code decided)"):
            st.json(s.last.model_dump())
