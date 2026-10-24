"use client";

import { useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  FileText,
  LoaderCircle,
  Pencil,
  Quote,
  X,
} from "lucide-react";
import {
  Commitment,
  CommitmentChanges,
  dateLabel,
  isCalendarDate,
  isOverdue,
  needsReview,
  statusLabel,
} from "../lib/commitments";

type Props = {
  item: Commitment;
  busy: boolean;
  compact?: boolean;
  onUpdate: (item: Commitment, changes: CommitmentChanges) => Promise<boolean>;
  onDraft: (item: Commitment) => Promise<void>;
};

export default function CommitmentCard({
  item,
  busy,
  compact,
  onUpdate,
  onDraft,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [claim, setClaim] = useState(item.claim);
  const [owner, setOwner] = useState(item.owner || "");
  const [recipient, setRecipient] = useState(item.recipient || "");
  const [deadline, setDeadline] = useState(item.deadline || "");
  const [note, setNote] = useState(item.notes || "");
  const [validation, setValidation] = useState("");

  function beginEdit() {
    setClaim(item.claim);
    setOwner(item.owner || "");
    setRecipient(item.recipient || "");
    setDeadline(item.deadline || "");
    setNote(item.notes || "");
    setValidation("");
    setEditing(true);
  }

  async function save() {
    if (!claim.trim()) {
      setValidation("Add a short description of the commitment.");
      return;
    }
    if (deadline.trim() && !isCalendarDate(deadline.trim())) {
      setValidation("Use a date in YYYY-MM-DD format, or leave it blank.");
      return;
    }
    if (
      await onUpdate(item, {
        claim: claim.trim(),
        owner: owner.trim() || null,
        recipient: recipient.trim() || null,
        deadline: deadline.trim() || null,
        note,
      })
    ) {
      setEditing(false);
    }
  }

  const overdue = isOverdue(item);
  const condition = item.conditionality?.replace(/^(?:if\s+)+/i, "");
  return (
    <article
      className={`commit-card ${compact ? "compact-card" : ""} ${overdue ? "overdue-card" : ""}`}
      aria-label={item.claim}
      data-commitment-id={item.id}
    >
      <div className="commit-top">
        <span className={`status-badge status-${item.status}`}>
          <span />
          {statusLabel[item.status]}
        </span>
        <span className={`due-label ${overdue ? "past-due" : ""}`}>
          <CalendarDays size={13} />
          {overdue ? "Past due · " : ""}
          {dateLabel(item.deadline)}
        </span>
      </div>
      {editing ? (
        <div className="edit-form">
          <h3>Edit this promise</h3>
          <label>
            Commitment
            <input
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              maxLength={500}
              autoFocus
            />
          </label>
          <label>
            Owner
            <input
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="Leave blank if unclear"
            />
          </label>
          <label>
            Recipient
            <input
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder="Optional"
            />
          </label>
          <label>
            Due date
            <input
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              placeholder="YYYY-MM-DD, or leave blank"
            />
          </label>
          <label>
            Private note
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={4000}
              placeholder="Context you want to remember"
            />
          </label>
          {validation && (
            <p role="alert" className="field-error">
              {validation}
            </p>
          )}
          <div className="edit-actions">
            <button className="button primary" onClick={save} disabled={busy}>
              {busy ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <Check size={15} />
              )}
              Save edits
            </button>
            <button
              className="button secondary"
              onClick={() => setEditing(false)}
              disabled={busy}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <h3>{item.claim}</h3>
          <div className="person-line">
            <span className={`person-avatar ${item.owner ? "" : "unknown"}`}>
              {item.owner?.slice(0, 1).toUpperCase() || "?"}
            </span>
            <span>{item.owner || "Owner to clarify"}</span>
            {item.recipient && (
              <>
                <ArrowRight size={12} />
                <span className="recipient">{item.recipient}</span>
              </>
            )}
          </div>
          <div className="evidence">
            <div className="evidence-heading">
              <Quote size={13} />
              <span>Exact source quote</span>
            </div>
            {(item.evidence_quotes?.length
              ? item.evidence_quotes
              : [item.evidence]
            ).map((quote, index) => (
              <blockquote key={`${index}-${quote}`}>{quote}</blockquote>
            ))}
            <details className="source-details">
              <summary>
                <FileText size={12} />
                <span>{item.source_name}</span>
                <ChevronDown size={12} />
              </summary>
              <p>
                {item.location
                  ? `Paragraph ${item.location.fragment + 1} · characters ${item.location.start}–${item.location.end}`
                  : "Quote checked against the original notes."}
              </p>
            </details>
          </div>
          {condition && (
            <p className="condition">
              <span />
              Conditional · If {condition}
            </p>
          )}
          {item.notes && (
            <div className="private-note">
              <span>Your note</span>
              {item.notes}
            </div>
          )}
          <div className="commit-actions">
            {needsReview(item) ? (
              <>
                <button
                  className="button primary"
                  onClick={() => onUpdate(item, { status: "confirmed" })}
                  disabled={busy}
                >
                  {busy ? (
                    <LoaderCircle size={14} className="spin" />
                  ) : (
                    <Check size={14} />
                  )}
                  Looks right
                </button>
                <button
                  className="button secondary"
                  onClick={beginEdit}
                  disabled={busy}
                >
                  <Pencil size={13} />
                  Edit
                </button>
                <button
                  className="button icon-button dismiss-button"
                  aria-label={`Dismiss ${item.claim}`}
                  title="Dismiss"
                  onClick={() => onUpdate(item, { status: "rejected" })}
                  disabled={busy}
                >
                  <X size={16} />
                </button>
              </>
            ) : item.status === "confirmed" ? (
              <>
                <button
                  className="button primary"
                  onClick={() => onDraft(item)}
                  disabled={busy}
                >
                  Draft follow-up
                  <ArrowRight size={14} />
                </button>
                <button
                  className="button secondary"
                  onClick={beginEdit}
                  disabled={busy}
                  aria-label={`Edit ${item.claim}`}
                >
                  <Pencil size={13} />
                  <span>Edit</span>
                </button>
                <button
                  className="button icon-button"
                  aria-label={`Mark ${item.claim} complete`}
                  title="Mark complete"
                  onClick={() => onUpdate(item, { status: "complete" })}
                  disabled={busy}
                >
                  <CheckCheck size={17} />
                </button>
              </>
            ) : (
              <span className="closed-label">
                {item.status === "complete" ? (
                  <CheckCheck size={15} />
                ) : (
                  <X size={15} />
                )}
                {item.status === "complete"
                  ? "All taken care of"
                  : "Dismissed from your queue"}
              </span>
            )}
          </div>
        </>
      )}
    </article>
  );
}
