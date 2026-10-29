"""IntakeSession: the state and the decisions. The model proposes; this code disposes.

The model is stateless and re-reads the whole conversation every turn. The session keeps the
case file, merges each new extraction into it, and decides on its own what is missing, whether
the case is complete, which question is asked, and which flags a reviewer sees. No I/O here
beyond the injected `extract` function, so every rule is unit-tested without the network.
"""
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from anthropic.types import MessageParam
from pydantic import BaseModel

from . import config
from .extract import IntakeError, extract_turn
from .prompt import cardholder_turn, first_turn
from .regime import Regime, select_regime
from .rules import hard_flags
from .schema import REQUIRED_FIELDS, CaseFile, ExtractionResult, Flag, get_path


def _leaf_paths(model: type[BaseModel], prefix: str = "") -> set[str]:
    paths = set()
    for name, info in model.model_fields.items():
        ann = info.annotation
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            paths |= _leaf_paths(ann, f"{prefix}{name}.")
        else:
            paths.add(f"{prefix}{name}")
    return paths


# Fields the model may ask about. Narrative is code-owned, so it is never a question target.
FIELD_WHITELIST: frozenset[str] = frozenset(_leaf_paths(CaseFile) - {"narrative"})

# Fallback wording, used when the model's own question is missing or targets the wrong field.
FALLBACK_QUESTIONS: dict[str, str] = {
    "dispute_type": "Could you tell me what went wrong with this payment?",
    "transaction.merchant_name": "What is the name of the shop or company that charged you?",
    "transaction.amount": "How much was the charge?",
    "transaction.currency": "Which currency was the charge in?",
    "transaction.date": "On which date did the charge happen?",
    "transaction.payment_method": "Was this a card payment or a direct debit from your account?",
    "transaction.issuer_country": "In which country is the bank that issued your card?",
    "cardholder.recognizes_merchant": "Do you recognise the shop or company that charged you?",
    "cardholder.card_in_possession": "Do you still have your card with you?",
    "cardholder.card_reported_lost_or_stolen": "Have you reported your card as lost or stolen?",
    "cardholder.authorized_third_party": "Has anyone else, such as a family member, been allowed to use your card?",
    "cardholder.contacted_merchant": "Have you contacted the merchant about this yet?",
    "cardholder.merchant_response": "What did the merchant say when you contacted them?",
    "cardholder.expected_delivery_date": "When were you expecting the order to arrive?",
    "cardholder.disputed_this_merchant_before": "Have you disputed a payment to this merchant before?",
    "cardholder.cancellation_date": "On which date did you cancel the subscription?",
}

MAX_TEXT_CHARS = 300
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"(?:https?://|www\.)\S+")
# Tolerates the spacing tricks seen in LLMail-Inject attacks: "contact @ contact . com".
_EMAIL = re.compile(r"[\w.+-]+\s*@\s*[\w-]+(?:\s*\.\s*[\w-]+)+")

# String fields the model writes in its own words. Dates, currency and country are already
# pattern- or length-checked by the schema; these are not, so code scrubs them.
FREE_TEXT_FIELDS = ("transaction.merchant_name", "cardholder.merchant_response",
                    "cardholder.expected_delivery_date", "cardholder.cancellation_date")


def merge_known(prev: CaseFile, new: CaseFile) -> CaseFile:
    """Copy a value from `new` only when it is stated (not None): known values survive turns
    where the model leaves them out, and a newly stated value replaces an older one."""

    def merge(a: dict, b: dict) -> dict:
        out = dict(a)
        for key, value in b.items():
            if isinstance(value, dict):
                out[key] = merge(a.get(key) or {}, value)
            elif value is not None:
                out[key] = value
        return out

    return CaseFile.model_validate(merge(prev.model_dump(), new.model_dump()))


def _scrub(text: str) -> str:
    """Model-written text is untrusted: no links, no email addresses, bounded length.
    Removals are labelled so a reviewer can see something was there."""
    text = _MD_LINK.sub(r"\1 [link removed]", text)
    text = _URL.sub("[link removed]", text)
    text = _EMAIL.sub("[email removed]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_TEXT_CHARS].rstrip()


def _scrub_case(case: CaseFile) -> CaseFile:
    case = case.model_copy(deep=True)
    for path in FREE_TEXT_FIELDS:
        group, name = path.split(".")
        value = getattr(getattr(case, group), name)
        if value is not None:
            setattr(getattr(case, group), name, _scrub(value) or None)
    return case


@dataclass
class StepResult:
    question: str | None
    question_field: str | None
    complete: bool


@dataclass
class FinalCase:
    case_file: CaseFile
    regime: Regime
    missing_fields: list[str]
    flags: list[Flag]
    turns: int
    complete: bool


@dataclass
class IntakeSession:
    filed_on: str
    extract: Callable[..., ExtractionResult] = extract_turn
    turn_cap: int = config.TURN_CAP
    history: list[MessageParam] = field(default_factory=list)
    case_file: CaseFile = field(default_factory=CaseFile)
    turns: int = 0
    last: ExtractionResult | None = None
    _texts: list[str] = field(default_factory=list)
    _semantic: dict[str, Flag] = field(default_factory=dict)

    # --- decisions (pure, from current state) ------------------------------------------------

    def missing_fields(self) -> list[str]:
        if self.case_file.dispute_type is None:
            return ["dispute_type"]
        return [p for p in REQUIRED_FIELDS[self.case_file.dispute_type]
                if get_path(self.case_file, p) is None]

    def is_complete(self) -> bool:
        return not self.missing_fields() or self.turns >= self.turn_cap

    def flags(self) -> list[Flag]:
        """Hard rules first (they win on a shared code), then every semantic flag seen so far."""
        out = {f.code: f for f in hard_flags(self.case_file, self.filed_on)}
        for code, f in self._semantic.items():
            out.setdefault(code, f)
        return list(out.values())

    def result(self) -> FinalCase:
        return FinalCase(case_file=self.case_file, regime=select_regime(self.case_file),
                         missing_fields=self.missing_fields(), flags=self.flags(),
                         turns=self.turns, complete=self.is_complete())

    # --- one conversation turn -------------------------------------------------------------------

    def step(self, user_text: str, **extract_kwargs) -> StepResult:
        """Send one cardholder message. Raises IntakeError; on error nothing is changed."""
        text = user_text.strip()
        if not text:
            raise IntakeError("empty_input", "Please type a message before sending.")
        if self.is_complete():
            return StepResult(None, None, True)

        message = first_turn(text, self.filed_on) if not self.history else cardholder_turn(text)
        candidate = [*self.history, message]
        extracted = self.extract(candidate, **extract_kwargs)  # may raise; state untouched

        # Commit only after a successful call, so a retry never duplicates the message.
        self.history = candidate
        self._texts.append(text)
        self.turns += 1
        self.last = extracted
        self.case_file = merge_known(self.case_file, _scrub_case(extracted.case_file))
        self.case_file.narrative = "\n".join(self._texts)  # code-owned, model's value discarded
        for f in extracted.semantic_flags:
            self._semantic.setdefault(f.code, f)

        if self.is_complete():
            return StepResult(None, None, True)

        field_, question = self._choose_question(extracted)
        self.history.append({"role": "assistant", "content": question})
        return StepResult(question, field_, False)

    def _choose_question(self, extracted: ExtractionResult) -> tuple[str, str]:
        # Keep the model's question only if it targets a required field that is still missing.
        # Eval v1 showed why: questions about optional fields ("have you disputed this merchant
        # before?") used up the turn cap before required ones were asked.
        q = extracted.next_question
        # Seen live: the model sometimes prefixes the path with its schema root
        # ("case_file.dispute_type"). Strip that one prefix; the whitelist still applies.
        path = q.field.removeprefix("case_file.") if q else None
        if q and path in FIELD_WHITELIST and path in self.missing_fields():
            text = _scrub(q.text)
            if text:
                return path, text
        target = self.missing_fields()[0]
        return target, FALLBACK_QUESTIONS[target]
