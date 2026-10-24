from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, Boolean, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'promisekeeper.db'}")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class SourceDocument(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    source_timestamp: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    commitments: Mapped[list["Commitment"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    fragments: Mapped[list["SourceFragment"]] = relationship(back_populates="source", cascade="all, delete-orphan")

class SourceFragment(Base):
    __tablename__ = "fragments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[SourceDocument] = relationship(back_populates="fragments")

class Commitment(Base):
    __tablename__ = "commitments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    claim: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    recipient: Mapped[str | None] = mapped_column(String, nullable=True)
    deadline: Mapped[str | None] = mapped_column(String, nullable=True)
    conditionality: Mapped[str | None] = mapped_column(Text, nullable=True)
    certainty: Mapped[str] = mapped_column(String, default="suggested")
    status: Mapped[str] = mapped_column(String, default="suggested")
    evidence: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    fragment_id: Mapped[str | None] = mapped_column(ForeignKey("fragments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    source: Mapped[SourceDocument] = relationship(back_populates="commitments")
    fragment: Mapped[SourceFragment | None] = relationship()
    drafts: Mapped[list["Draft"]] = relationship(back_populates="commitment", cascade="all, delete-orphan")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="commitment", cascade="all, delete-orphan")
    evidence_records: Mapped[list["Evidence"]] = relationship(back_populates="commitment", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    commitment_id: Mapped[str] = mapped_column(ForeignKey("commitments.id", ondelete="CASCADE"))
    fragment_id: Mapped[str | None] = mapped_column(ForeignKey("fragments.id"), nullable=True)
    quote: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int | None] = mapped_column(nullable=True)
    end_offset: Mapped[int | None] = mapped_column(nullable=True)
    commitment: Mapped[Commitment] = relationship(back_populates="evidence_records")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    commitment_id: Mapped[str] = mapped_column(ForeignKey("commitments.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String)
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    commitment: Mapped[Commitment] = relationship(back_populates="audit_events")

class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    commitment_id: Mapped[str] = mapped_column(ForeignKey("commitments.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    commitment: Mapped[Commitment] = relationship(back_populates="drafts")

Base.metadata.create_all(engine)
app = FastAPI(title="PromiseKeeper API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:3001"], allow_methods=["*"], allow_headers=["*"])

class ImportBody(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    name: str = Field(default="Pasted notes", max_length=240)
    source_timestamp: datetime | None = None

class ExtractedCommitment(BaseModel):
    claim: str = Field(min_length=1, max_length=500)
    owner: str | None = None
    recipient: str | None = None
    deadline: str | None = None
    conditionality: str | None = None
    certainty: Literal["suggested", "ambiguous"] = "suggested"
    evidence: str = Field(min_length=1)
    action: str = Field(min_length=1)

class CommitmentPatch(BaseModel):
    claim: str | None = None
    owner: str | None = None
    recipient: str | None = None
    deadline: str | None = None
    status: Literal["suggested", "ambiguous", "confirmed", "complete", "rejected"] | None = None
    note: str | None = Field(default=None, max_length=4000)

class DraftBody(BaseModel):
    tone: str = "polite"

def serialize(c: Commitment):
    return {"id": c.id, "claim": c.claim, "owner": c.owner, "recipient": c.recipient, "deadline": c.deadline,
            "conditionality": c.conditionality, "certainty": c.certainty, "status": c.status, "evidence": c.evidence,
            "action": c.action, "source_id": c.source_id, "source_name": c.source.name if c.source else "", "fragment_id": c.fragment_id,
            "location": {"start": c.fragment.start_offset, "end": c.fragment.end_offset, "fragment": c.fragment.ordinal} if c.fragment else None, "notes": c.notes,
            "evidence_quotes": [record.quote for record in c.evidence_records] or [c.evidence],
            "created_at": c.created_at.isoformat()}

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

async def extract_local(text: str, source_timestamp: datetime | None):
    prompt = f'''Find only commitments or clear obligations in these notes. A commitment is a person agreeing to do something, or an explicit obligation assigned to them. Ignore negated, hypothetical, sarcastic and already fulfilled statements. Never infer a name/date that is not explicit. Dates such as "tomorrow" may be resolved only when a source timestamp is provided; otherwise leave deadline null. Return strict JSON object {{"commitments":[{{"claim":"short action","owner":null,"recipient":null,"deadline":null,"conditionality":null,"certainty":"suggested|ambiguous","evidence":"verbatim exact source quote","action":"proposed next action"}}]}}. Every quote must be an exact substring of the source. Source timestamp: {source_timestamp.isoformat() if source_timestamp else "unknown"}. Text:\n{text}'''
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "prompt": prompt + "\n/no_think", "stream": False, "format": "json", "think": False, "options": {"temperature": 0, "num_predict": 512}})
        response.raise_for_status()
    raw = json.loads(response.json()["response"])
    found = []
    for item in raw.get("commitments", []):
        evidence = str(item.get("evidence", ""))
        if evidence and evidence in text and item.get("claim") and not non_commitment_quote(evidence):
            found.append({"claim": item["claim"], "owner": item.get("owner"), "recipient": item.get("recipient"),
                          "deadline": resolve_deadline_text(item.get("deadline"), source_timestamp), "conditionality": item.get("conditionality"),
                          "certainty": item.get("certainty", "suggested"), "evidence": evidence,
                          "action": item.get("action") or "Review this commitment"})
    return found

@app.get("/api/health")
async def health():
    available = False; installed = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            tags = (await client.get(f"{OLLAMA_URL}/api/tags")).json().get("models", [])
            installed = any(m["name"] == OLLAMA_MODEL or m["name"].startswith(OLLAMA_MODEL + ":") for m in tags)
            available = True
    except Exception: pass
    return {"api": "ok", "model": OLLAMA_MODEL, "ollama_available": available, "model_installed": installed, "inference": "local"}

@app.post("/api/import")
async def import_text(body: ImportBody):
    if not body.text.strip(): raise HTTPException(422, "Source text is empty")
    with Session() as db:
        source = SourceDocument(name=body.name, text=body.text, source_timestamp=body.source_timestamp.isoformat() if body.source_timestamp else None)
        db.add(source); db.flush()
        fragments = []
        for match in re.finditer(r"\S(?:.*?\S)?(?=\s*\n\s*\n|\Z)", body.text, re.S):
            fragment = SourceFragment(source_id=source.id, ordinal=len(fragments), start_offset=match.start(), end_offset=match.end(), text=match.group().strip())
            db.add(fragment); fragments.append(fragment)
        db.flush()
        try: items = await extract_local(body.text, body.source_timestamp)
        except Exception as exc:
            db.rollback(); raise HTTPException(503, f"Local model unavailable or returned invalid output: {exc}")
        # Keep the safety boundary at the API layer too: model adapter output is
        # untrusted, and this check remains in force for any future adapter.
        accepted = 0
        grouped = {}
        for item in items:
            try:
                checked = ExtractedCommitment.model_validate(item)
            except Exception:
                continue
            if checked.evidence not in body.text or non_commitment_quote(checked.evidence):
                continue
            fragment = next((f for f in fragments if checked.evidence in f.text), None)
            key = (re.sub(r"\W+", " ", checked.claim.casefold()).strip(), (checked.owner or "").casefold(), (checked.recipient or "").casefold(), (checked.deadline or "").casefold())
            existing = grouped.get(key)
            if existing:
                if checked.evidence not in {e.quote for e in existing.evidence_records}:
                    start = fragment.start_offset + fragment.text.find(checked.evidence) if fragment else body.text.find(checked.evidence)
                    db.add(Evidence(commitment=existing, fragment_id=fragment.id if fragment else None, quote=checked.evidence, start_offset=start, end_offset=start + len(checked.evidence) if start >= 0 else None))
                continue
            commitment = Commitment(source_id=source.id, fragment_id=fragment.id if fragment else None, **checked.model_dump())
            db.add(commitment); db.flush(); grouped[key] = commitment
            start = fragment.start_offset + fragment.text.find(checked.evidence) if fragment else body.text.find(checked.evidence)
            db.add(Evidence(commitment_id=commitment.id, fragment_id=fragment.id if fragment else None, quote=checked.evidence, start_offset=start, end_offset=start + len(checked.evidence) if start >= 0 else None))
            accepted += 1
        db.commit()
        return {"source_id": source.id, "source_name": source.name, "commitments": [serialize(c) for c in source.commitments], "count": accepted}

@app.post("/api/import/file")
async def import_file(file: UploadFile = File(...)):
    if Path(file.filename or "").suffix.lower() not in {".txt", ".md"}: raise HTTPException(415, "Import .txt or .md files")
    content = (await file.read(200_001)).decode("utf-8", errors="replace")
    return await import_text(ImportBody(text=content, name=file.filename or "Imported notes"))

@app.get("/api/commitments")
def list_commitments(status: str | None = None, q: str | None = None):
    with Session() as db:
        query = select(Commitment).order_by(Commitment.created_at.desc())
        if status: query = query.where(Commitment.status == status)
        rows = db.scalars(query).all()
        if q: rows = [c for c in rows if q.casefold() in (c.claim + c.evidence + (c.owner or "")).casefold()]
        return [serialize(c) for c in rows]

@app.patch("/api/commitments/{commitment_id}")
def update_commitment(commitment_id: str, body: CommitmentPatch):
    with Session() as db:
        c = db.get(Commitment, commitment_id)
        if not c: raise HTTPException(404, "Commitment not found")
        changes = body.model_dump(exclude_unset=True)
        previous_status = c.status
        if "status" in changes: c.status = changes["status"]
        for key, value in changes.items():
            if key == "note": c.notes = value or ""
            elif key not in {"status", "note"}: setattr(c, key, value)
        if changes:
            db.add(AuditEvent(commitment_id=c.id, action="updated", details=json.dumps({"changes": changes, "previous_status": previous_status}, ensure_ascii=False)))
        db.commit(); db.refresh(c); return serialize(c)

@app.post("/api/commitments/{commitment_id}/draft")
def create_draft(commitment_id: str, body: DraftBody):
    with Session() as db:
        c = db.get(Commitment, commitment_id)
        if not c or c.status != "confirmed": raise HTTPException(409, "Only an approved, open commitment can be drafted")
        who = c.owner or "there"
        subject = re.sub(r"^(?:send|share|upload|prepare|draft|deliver|submit|complete|finish|check|update|review|provide|write|build|create)\s+", "", c.claim.strip(), flags=re.I) or c.claim
        timing = f" I had noted {c.deadline} as the timing; please let me know if that has shifted." if c.deadline else ""
        text = f"Hi {who},\n\nI wanted to check in about {subject}.{timing}\n\nWhen you have a moment, could you share an update?\n\nThanks!"
        draft = Draft(commitment_id=c.id, text=text); db.add(draft); db.commit()
        return {"id": draft.id, "text": draft.text, "requires_human_review": True, "sent": False}

@app.get("/api/dashboard")
def dashboard():
    rows = list_commitments()
    today = date.today().isoformat()
    counts = {s: sum(1 for c in rows if c["status"] == s) for s in ["suggested", "ambiguous", "confirmed", "complete"]}
    confirmed = [c for c in rows if c["deadline"] and c["status"] == "confirmed"]
    overdue = [c for c in confirmed if c["deadline"] < today]
    return {"counts": counts, "unassigned": sum(1 for c in rows if not c["owner"] and c["status"] != "complete"), "overdue": overdue, "upcoming": [c for c in confirmed if c["deadline"] >= today]}

@app.get("/api/export")
def export():
    import csv, io
    rows = [c for c in list_commitments() if c["status"] == "confirmed"]
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=["claim", "owner", "recipient", "deadline", "evidence", "source_name"])
    writer.writeheader(); writer.writerows([{k: c[k] for k in writer.fieldnames} for c in rows])
    return {"csv": output.getvalue(), "count": len(rows)}

@app.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    with Session() as db:
        source = db.get(SourceDocument, source_id)
        if not source: raise HTTPException(404, "Source not found")
        db.delete(source); db.commit(); return {"deleted": True}

@app.get("/api/sources")
def list_sources():
    with Session() as db:
        return [{"id": s.id, "name": s.name, "created_at": s.created_at.isoformat(), "commitments": len(s.commitments)} for s in db.scalars(select(SourceDocument)).all()]
