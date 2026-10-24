export type Status =
  | "suggested"
  | "ambiguous"
  | "confirmed"
  | "complete"
  | "rejected";

export type Commitment = {
  id: string;
  claim: string;
  owner: string | null;
  recipient: string | null;
  deadline: string | null;
  conditionality: string | null;
  certainty: string;
  status: Status;
  evidence: string;
  evidence_quotes?: string[];
  source_id: string;
  source_name: string;
  location?: { start: number; end: number; fragment: number } | null;
  notes?: string;
  created_at?: string;
};

export type CommitmentChanges = {
  claim?: string;
  owner?: string | null;
  recipient?: string | null;
  deadline?: string | null;
  note?: string;
  status?: Status;
};

export type Source = {
  id: string;
  name: string;
  created_at: string;
  commitments: number;
};
export type Health = {
  model: string;
  ollama_available: boolean;
  model_installed: boolean;
};
export type View =
  | "Overview"
  | "Review inbox"
  | "Timeline"
  | "Follow-ups"
  | "Privacy"
  | "Import notes";

export function localDate() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function isCalendarDate(value: string | null): value is string {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T12:00:00Z`);
  return (
    !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  );
}

export function dateLabel(value: string | null) {
  if (!value) return "No date yet";
  if (!isCalendarDate(value)) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

export function needsReview(item: Commitment) {
  return item.status === "suggested" || item.status === "ambiguous";
}

export function isOverdue(item: Commitment) {
  return (
    item.status === "confirmed" &&
    isCalendarDate(item.deadline) &&
    item.deadline < localDate()
  );
}

export function sortCommitments(items: Commitment[]) {
  const priority = (item: Commitment) =>
    isOverdue(item)
      ? 0
      : needsReview(item)
        ? 1
        : item.status === "confirmed"
          ? 2
          : 3;
  return [...items].sort(
    (a, b) =>
      priority(a) - priority(b) ||
      (isCalendarDate(a.deadline) ? a.deadline : "9999").localeCompare(
        isCalendarDate(b.deadline) ? b.deadline : "9999",
      ) ||
      (b.created_at || "").localeCompare(a.created_at || ""),
  );
}

export const statusLabel: Record<Status, string> = {
  suggested: "Needs review",
  ambiguous: "Needs context",
  confirmed: "Confirmed",
  complete: "Complete",
  rejected: "Dismissed",
};
