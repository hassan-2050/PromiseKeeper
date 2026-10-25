"""Shared extraction boundary; importing it never opens the application database."""
from datetime import datetime, timedelta
from typing import Literal
import re
from pydantic import BaseModel, Field

class ExtractedCommitment(BaseModel):
    claim: str = Field(min_length=1, max_length=500)
    owner: str | None = None
    recipient: str | None = None
    deadline: str | None = None
    conditionality: str | None = None
    certainty: Literal["suggested", "ambiguous"] = "suggested"
    evidence: str = Field(min_length=1)
    action: str = Field(min_length=1)

def non_commitment_quote(quote: str) -> bool:
    """Conservative lexical gate for clear refusals, completed actions and hypotheticals."""
    clause = re.split(r"\bbut\b", quote, flags=re.I)[-1].casefold()
    if re.search(r"\b(?:won['’]?t|will not|can['’]?t|cannot|couldn['’]?t|wouldn['’]?t|not going to|not be able to)\b", clause):
        return True
    if re.search(r"\b(?:already\s+)?(?:sent|shared|uploaded|finished|completed|submitted|delivered|provided)\b", clause):
        return True
    has_intent = re.search(r"\b(?:i['’]?ll|we['’]?ll|i will|we will|i can|we can|i am going to|we are going to)\b", clause)
    if re.search(r"\b(?:could|might|would)\b", clause) and not has_intent:
        return True
    return False

def resolve_deadline_text(deadline: str | None, source_timestamp: datetime | None) -> str | None:
    if not deadline:
        return None
    has_calendar_date = bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", deadline))
    phrase = re.sub(r"^(?:by|on|due)\s+", "", deadline.strip().casefold())
    relative = re.search(r"\b(?:today|tomorrow|tonight|soon|shortly|later|next\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|this\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|monday|tuesday|wednesday|thursday|friday|saturday|sunday|in\s+\d+\s+days?)\b", phrase)
    if not relative or has_calendar_date:
        return deadline
    if not source_timestamp:
        return None
    base = source_timestamp.date()
    if re.fullmatch(r"today(?: morning| afternoon| evening)?|tonight", phrase): return base.isoformat()
    if re.fullmatch(r"tomorrow(?: morning| afternoon| evening)?", phrase): return (base + timedelta(days=1)).isoformat()
    in_days = re.fullmatch(r"in\s+(\d+)\s+days?", phrase)
    if in_days: return (base + timedelta(days=int(in_days.group(1)))).isoformat()
    weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    match = re.fullmatch(r"(?:(next|this)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", phrase)
    if match:
        modifier, day = match.groups(); delta = (weekdays[day] - base.weekday()) % 7
        if modifier == "next" and delta == 0: delta = 7
        if modifier == "this" and delta == 0: delta = 0
        return (base + timedelta(days=delta)).isoformat()
    # Vague timing words are never converted into invented calendar dates.
    return None

def build_prompt(text: str, source_timestamp: datetime | None):
    return f'''Find only commitments or clear obligations in these notes. A commitment is a person agreeing to do something, or an explicit obligation assigned to them. Ignore negated, hypothetical, sarcastic and already fulfilled statements. Never infer a name/date that is not explicit. Dates such as "tomorrow" may be resolved only when a source timestamp is provided; otherwise leave deadline null. Return strict JSON object {{"commitments":[{{"claim":"short action","owner":null,"recipient":null,"deadline":null,"conditionality":null,"certainty":"suggested|ambiguous","evidence":"verbatim exact source quote","action":"proposed next action"}}]}}. Every quote must be an exact substring of the source. Source timestamp: {source_timestamp.isoformat() if source_timestamp else "unknown"}. Text:\n{text}'''
