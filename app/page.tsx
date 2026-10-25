"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  Clock3,
  Copy,
  FileText,
  FolderOpen,
  Inbox,
  LayoutDashboard,
  Leaf,
  LoaderCircle,
  LockKeyhole,
  Menu,
  MessageSquareText,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import CommitmentCard from "./components/commitment-card";
import { api } from "./lib/api";
import {
  Commitment,
  CommitmentChanges,
  Health,
  Source,
  View,
  dateLabel,
  isCalendarDate,
  isOverdue,
  localDate,
  needsReview,
  sortCommitments,
} from "./lib/commitments";

const SAMPLE = `SYNTHETIC DEMO - Research notes, 2026-10-21. No real conversations.

Maya: I'll send the revised field report by 2026-10-23 so you can include it in the packet.

Jon: I can share the cleaned survey figures by 2026-10-27.

Maya: If the lab clears the samples, I'll upload the appendix.

Jon: I already sent the consent forms this morning.

Maya: We should probably talk about the conference sometime.`;

const NAV = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Review inbox", icon: Inbox },
  { name: "Timeline", icon: CalendarDays },
  { name: "Follow-ups", icon: MessageSquareText },
  { name: "Privacy", icon: ShieldCheck },
] as const;

const PAGE_COPY: Record<
  Exclude<View, "Overview">,
  { label: string; description: string }
> = {
  "Review inbox": {
    label: "A promise starts with the evidence.",
    description:
      "Check the original words. Keep what matters, and let the rest go.",
  },
  "Import notes": {
    label: "Bring the conversation with you.",
    description:
      "A meeting, a transcript, a few scattered notes. Start wherever you are.",
  },
  Timeline: {
    label: "A little room to plan ahead.",
    description: "Your confirmed promises, arranged by the dates you reviewed.",
  },
  "Follow-ups": {
    label: "A thoughtful nudge, in your words.",
    description:
      "Prepare a draft, make it your own, and decide what happens next.",
  },
  Privacy: {
    label: "Your conversations. Your space.",
    description:
      "Know where your notes live, take a copy, or clear what you no longer need.",
  },
};

type Draft = { itemId: string; text: string };

export default function Home() {
  const [items, setItems] = useState<Commitment[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [view, setView] = useState<View>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("review");
  const [text, setText] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceTimestamp, setSourceTimestamp] = useState("");
  const [importing, setImporting] = useState(false);
  const [remoteConsent, setRemoteConsent] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [manageSources, setManageSources] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const helpDialog = useRef<HTMLDialogElement>(null);
  const importInput = useRef<HTMLTextAreaElement>(null);
  const navigation = useRef<HTMLElement>(null);

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    const results = await Promise.allSettled([
      api<Commitment[]>("/commitments"),
      api<Source[]>("/sources"),
      api<Health>("/health"),
    ]);
    if (results[0].status === "fulfilled") setItems(results[0].value);
    else
      setError(
        results[0].reason instanceof Error
          ? results[0].reason.message
          : "Could not load your promises.",
      );
    if (results[1].status === "fulfilled") setSources(results[1].value);
    setHealth(results[2].status === "fulfilled" ? results[2].value : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    setRemoteConsent(false);
  }, [text, sourceTimestamp, health?.inference]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 6500);
    return () => window.clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!mobileOpen) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const buttons = () =>
      Array.from(
        navigation.current?.querySelectorAll<HTMLButtonElement>(
          "button:not([disabled])",
        ) || [],
      ).filter((button) => button.getClientRects().length);
    document.body.style.overflow = "hidden";
    const frame = window.requestAnimationFrame(() => buttons()[0]?.focus());
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
      }
      if (event.key === "Tab") {
        const targets = buttons();
        const first = targets[0],
          last = targets[targets.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = "";
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", handleKey);
      previousFocus?.focus();
    };
  }, [mobileOpen]);

  const remote = health?.inference === "remote";
  const ready = remote
    ? Boolean(health?.model_available)
    : Boolean(health?.model_installed && health?.ollama_available);
  const active = items.filter(
    (item) => item.status !== "rejected" && item.status !== "complete",
  );
  const reviewItems = items.filter(needsReview);
  const confirmed = items.filter((item) => item.status === "confirmed");
  const overdue = items.filter(isOverdue);
  const unclear = active.filter((item) => !item.owner);
  const upcoming = [...confirmed]
    .filter(
      (item) => isCalendarDate(item.deadline) && item.deadline >= localDate(),
    )
    .sort((a, b) => (a.deadline || "").localeCompare(b.deadline || ""));
  const nextMoves = sortCommitments(active).slice(0, 3);
  const filtered = sortCommitments(items).filter((item) => {
    const matches =
      filter === "all" ||
      (filter === "review"
        ? needsReview(item)
        : filter === "overdue"
          ? isOverdue(item)
          : filter === "unassigned"
            ? !item.owner && active.some((a) => a.id === item.id)
            : item.status === filter);
    const words =
      `${item.claim} ${item.evidence} ${item.owner || ""} ${item.recipient || ""} ${item.source_name}`.toLowerCase();
    return matches && words.includes(query.toLowerCase());
  });
  const timeline = useMemo(() => {
    const groups: Record<string, Commitment[]> = {};
    [...items]
      .filter((item) => item.status === "confirmed")
      .sort((a, b) =>
        (isCalendarDate(a.deadline) ? a.deadline : "9999").localeCompare(
          isCalendarDate(b.deadline) ? b.deadline : "9999",
        ),
      )
      .forEach((item) => {
        const date = isCalendarDate(item.deadline) ? item.deadline : "undated";
        (groups[date] ||= []).push(item);
      });
    return Object.entries(groups);
  }, [items]);

  function navigate(next: View, nextFilter?: string) {
    setView(next);
    setMobileOpen(false);
    setError("");
    if (next === "Review inbox") {
      setFilter(nextFilter || "review");
      setQuery("");
    }
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function sample() {
    setText(SAMPLE);
    setSourceName("Research notes (synthetic sample)");
    setSourceTimestamp("2026-10-21T09:00");
    navigate("Import notes");
  }

  async function ingest() {
    if (!text.trim() || importing) return;
    if (remote && !remoteConsent) {
      setError("Confirm that these notes may be sent to Tinker for this import.");
      return;
    }
    setImporting(true);
    setError("");
    try {
      const data = await api<{ count: number }>("/import", {
        method: "POST",
        body: JSON.stringify({
          text,
          name: sourceName.trim() || "Pasted notes",
          source_timestamp: sourceTimestamp || null,
          allow_remote_inference: remote && remoteConsent,
        }),
      });
      await refresh(true);
      setText("");
      setSourceName("");
      setSourceTimestamp("");
      setView("Review inbox");
      setFilter("review");
      setQuery("");
      setNotice(
        data.count
          ? `${data.count} possible ${data.count === 1 ? "promise is" : "promises are"} ready for your review.`
          : "Notes saved. No supported commitments were found.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not process these notes.",
      );
    } finally {
      setImporting(false);
    }
  }

  async function update(item: Commitment, changes: CommitmentChanges) {
    setBusyId(item.id);
    setError("");
    try {
      const saved = await api<Commitment>(`/commitments/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      setItems((current) =>
        current.map((row) => (row.id === item.id ? saved : row)),
      );
      if (
        changes.status &&
        changes.status !== "confirmed" &&
        draft?.itemId === item.id
      )
        setDraft(null);
      setNotice(
        changes.status === "confirmed"
          ? "Promise confirmed. You can prepare a follow-up whenever you need one."
          : changes.status === "complete"
            ? "Marked complete. One less thing on your mind."
            : changes.status === "rejected"
              ? "Suggestion dismissed."
              : "Your edits were saved.",
      );
      return true;
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not update this promise.",
      );
      return false;
    } finally {
      setBusyId(null);
    }
  }

  async function makeDraft(item: Commitment) {
    setBusyId(item.id);
    setError("");
    setView("Follow-ups");
    try {
      const data = await api<{ text: string }>(
        `/commitments/${item.id}/draft`,
        { method: "POST", body: "{}" },
      );
      setDraft({ itemId: item.id, text: data.text });
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not prepare your draft.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function loadFile(file?: File) {
    if (!file) return;
    if (!/\.(txt|md)$/i.test(file.name)) {
      setError("Choose a .txt or .md file.");
      return;
    }
    if (file.size > 200_000) {
      setError("Choose a text file smaller than 200 KB.");
      return;
    }
    setText(await file.text());
    setSourceName(file.name);
    setNotice("File added. Check the notes, then find the promises.");
    importInput.current?.focus();
  }

  async function removeSource(source: Source) {
    setBusyId(source.id);
    setError("");
    try {
      await api(`/sources/${source.id}`, { method: "DELETE" });
      if (
        items.some(
          (item) => item.source_id === source.id && item.id === draft?.itemId,
        )
      )
        setDraft(null);
      setDeleteId(null);
      await refresh(true);
      setNotice("Source and its linked promises and drafts were deleted.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not delete the source.",
      );
    } finally {
      setBusyId(null);
    }
  }

  function download(content: string, filename: string, type: string) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function exportConfirmed() {
    setExporting(true);
    setError("");
    try {
      const data = await api<{ csv: string; count: number }>("/export");
      download(data.csv, "confirmed-promises.csv", "text/csv");
      setNotice(
        `Exported ${data.count} confirmed ${data.count === 1 ? "promise" : "promises"}.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not export your promises.",
      );
    } finally {
      setExporting(false);
    }
  }

  async function copyDraft() {
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(draft.text);
      setNotice("Draft copied. Review it before sending.");
    } catch {
      setError(
        "Could not copy automatically. You can select the text or download your draft.",
      );
    }
  }

  const card = (item: Commitment, compact = false) => (
    <CommitmentCard
      key={item.id}
      item={item}
      compact={compact}
      busy={busyId === item.id}
      onUpdate={update}
      onDraft={makeDraft}
    />
  );

  return (
    <main className="app-shell">
      <a className="skip-link" href="#workspace-content">
        Skip to workspace
      </a>
      {mobileOpen && (
        <button
          className="sidebar-scrim"
          aria-label="Dismiss navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        ref={navigation}
        role={mobileOpen ? "dialog" : undefined}
        aria-modal={mobileOpen ? true : undefined}
        aria-label={mobileOpen ? "Workspace navigation" : undefined}
        className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}
        id="workspace-navigation"
      >
        <div className="sidebar-brand">
          <div className="brand-mark">
            <CheckCheck size={23} strokeWidth={2} />
          </div>
          <span>
            promise<span>keeper</span>
          </span>
          <button
            className="sidebar-close icon-button"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={19} />
          </button>
        </div>
        <div className="workspace-label">
          <span className="workspace-initial">P</span>
          <div>
            <strong>Personal workspace</strong>
            <span>{remote ? "Local workspace. Tinker enabled." : "Just you. On this device."}</span>
          </div>
          <LockKeyhole size={13} />
        </div>
        <p className="nav-caption">YOUR WORKSPACE</p>
        <nav aria-label="Workspace navigation">
          {NAV.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={`nav-item ${view === name ? "selected" : ""}`}
              aria-label={name}
              aria-current={view === name ? "page" : undefined}
              onClick={() => navigate(name)}
            >
              <Icon size={19} />
              <span>{name}</span>
              {name === "Review inbox" && reviewItems.length > 0 && (
                <span className="nav-count">{reviewItems.length}</span>
              )}
              {view === name && name !== "Review inbox" && (
                <span className="nav-selected-dot" />
              )}
            </button>
          ))}
        </nav>
        <button
          className="sidebar-add"
          onClick={() => navigate("Import notes")}
        >
          <Plus size={17} />
          Import notes
        </button>
        <div className="sidebar-bottom">
          <div className="local-model-card">
            <span className={`connection-dot ${ready ? "connected" : ""}`} />
            <div>
              <strong>
                {loading
                  ? "Checking model"
                  : ready
                    ? remote ? "Tinker is configured" : "Local AI is ready"
                    : remote ? "Tinker needs setup" : "Local AI is offline"}
              </strong>
              <span>{health?.model || "Ollama"}</span>
            </div>
            <Leaf size={17} />
            <p>
              {remote ? "Cloud inference is enabled. Each import needs your consent." : <>Your notes stay close.<br />Inference runs on your device.</>}
            </p>
          </div>
          <button
            className="sidebar-settings"
            onClick={() => navigate("Privacy")}
          >
            <ShieldCheck size={18} />
            <span>{remote ? "Cloud data settings" : "Private by default"}</span>
            <ChevronRight size={15} />
          </button>
        </div>
      </aside>
      <div className="main-workspace" inert={mobileOpen}>
        <header className="topbar">
          <div className="topbar-location">
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              aria-expanded={mobileOpen}
              aria-controls="workspace-navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={22} />
            </button>
            <span>My workspace</span>
            <ChevronRight size={13} />
            <strong>{view}</strong>
          </div>
          <div className="topbar-tools">
            <span className={`model-pill ${ready ? "model-ready" : ""}`}>
              <span className="connection-dot" />
              {loading
                ? "Checking model"
                : ready
                  ? remote ? "Tinker · cloud AI" : "On-device AI"
                  : "Model offline"}
            </span>
            <button
              className="icon-button help-button"
              aria-label="Help"
              onClick={() => helpDialog.current?.showModal()}
            >
              <CircleHelp size={19} />
            </button>
          </div>
        </header>
        <div className="content" id="workspace-content">
          {view === "Overview" ? (
            <section className="overview-hero">
              <div>
                <span className="eyebrow">
                  <span />A LITTLE LESS TO KEEP IN YOUR HEAD
                </span>
                <h1>
                  Less chasing.
                  <br />
                  <span>More follow-through.</span>
                </h1>
                <p>Turn the things people say into next steps you can trust.</p>
                <button
                  className="button hero-button"
                  onClick={() => navigate("Import notes")}
                >
                  <Plus size={17} />
                  Import notes
                  <ArrowRight size={16} />
                </button>
              </div>
              <div className="hero-art" aria-hidden="true">
                <div className="hero-orbit orbit-one" />
                <div className="hero-orbit orbit-two" />
                <div className="art-page page-back" />
                <div className="art-page page-front">
                  <span className="art-quote">“</span>
                  <i />
                  <i />
                  <i />
                  <div className="art-stamp">
                    <Check size={23} />
                  </div>
                </div>
                <span className="art-spark">✳</span>
                <div className="art-caption">
                  <ShieldCheck size={13} />
                  The words. The context. Your call.
                </div>
              </div>
            </section>
          ) : (
            <div className="page-heading">
              <div>
                <span className="eyebrow">{PAGE_COPY[view].label}</span>
                <h1>{view}</h1>
                <p>{PAGE_COPY[view].description}</p>
              </div>
              {view !== "Import notes" && (
                <button
                  className="button primary heading-import"
                  onClick={() => navigate("Import notes")}
                >
                  <Plus size={16} />
                  Import notes
                </button>
              )}
            </div>
          )}
          {error && (
            <div role="alert" className="feedback error-feedback">
              <CircleHelp size={18} />
              <span>{error}</span>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="feedback notice-feedback">
              <Check size={17} />
              <span>{notice}</span>
              <button
                className="icon-button"
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading-state" role="status">
              <LoaderCircle className="spin" size={25} />
              <span>Opening your workspace...</span>
            </div>
          ) : (
            <>
              {view === "Overview" && (
                <>
                  <div className="stats" aria-label="Workspace summary">
                    {[
                      {
                        label: "Needs a look",
                        count: reviewItems.length,
                        detail: "Possible promises to review",
                        icon: Inbox,
                        tone: "mint",
                      },
                      {
                        label: "Confirmed",
                        count: confirmed.length,
                        detail: "Checked and approved by you",
                        icon: CheckCheck,
                        tone: "forest",
                      },
                      {
                        label: "Past due",
                        count: overdue.length,
                        detail: "Confirmed dates that passed",
                        icon: Clock3,
                        tone: "rose",
                      },
                      {
                        label: "Owner to clarify",
                        count: unclear.length,
                        detail: "A little more context needed",
                        icon: Search,
                        tone: "stone",
                      },
                    ].map(({ label, count, detail, icon: Icon, tone }) => (
                      <div className="stat-card" key={label} data-stat={label}>
                        <div>
                          <span className="stat-label">{label}</span>
                          <strong className="stat-value">
                            {count}
                            <span className={`stat-icon ${tone}`}>
                              <Icon size={20} />
                            </span>
                          </strong>
                          <p>{detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="overview-grid">
                    <section className="next-moves">
                      <div className="section-heading">
                        <div>
                          <span className="section-kicker">
                            A GOOD PLACE TO START
                          </span>
                          <h2>Your next moves</h2>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => navigate("Review inbox", "all")}
                        >
                          View all
                          <ArrowRight size={14} />
                        </button>
                      </div>
                      {nextMoves.length ? (
                        <div className="commitment-list">
                          {nextMoves.map((item) => card(item, true))}
                        </div>
                      ) : (
                        <div className="empty-state">
                          <div className="empty-symbol">
                            <Inbox size={29} />
                          </div>
                          <h3>A clearer head starts here.</h3>
                          <p>
                            Bring in a conversation. We'll help you find what
                            someone said they'd do, and keep the original words
                            close.
                          </p>
                          <button
                            className="button primary"
                            onClick={() => navigate("Import notes")}
                          >
                            <Plus size={16} />
                            Import your first notes
                          </button>
                          <button
                            className="text-button sample-button"
                            onClick={sample}
                          >
                            Explore with synthetic sample notes
                            <ArrowRight size={14} />
                          </button>
                        </div>
                      )}
                    </section>
                    <aside className="overview-rail">
                      <section className="upcoming-panel">
                        <div className="panel-heading">
                          <CalendarDays size={18} />
                          <h2>On the horizon</h2>
                        </div>
                        {upcoming.length ? (
                          <div className="upcoming-list">
                            {upcoming.slice(0, 3).map((item) => (
                              <div className="upcoming-item" key={item.id}>
                                <span className="small-date">
                                  {dateLabel(item.deadline)}
                                </span>
                                <strong>{item.claim}</strong>
                                <span>{item.owner || "Owner unclear"}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="rail-empty">
                            <span className="calendar-outline">
                              <CalendarDays size={24} />
                            </span>
                            <h3>A little breathing room.</h3>
                            <p>
                              No upcoming confirmed dates. Review a promise to
                              add it to your timeline.
                            </p>
                          </div>
                        )}
                        <button
                          className="text-button"
                          onClick={() => navigate("Timeline")}
                        >
                          Open timeline
                          <ArrowRight size={14} />
                        </button>
                      </section>
                      <section className="quiet-card">
                        <div className="quiet-card-icon">
                          <Leaf size={23} />
                        </div>
                        <h2>You set the pace.</h2>
                        <p>
                          A suggestion is a starting point. You decide what's a
                          real promise, and what can wait.
                        </p>
                        <span>
                          <ShieldCheck size={14} />
                          {remote ? "No follow-up messages sent for you" : "Nothing gets sent for you"}
                        </span>
                      </section>
                      <div className="source-count">
                        <FolderOpen size={16} />
                        <span>
                          {sources.length}{" "}
                          {sources.length === 1 ? "source" : "sources"} in your
                          private workspace
                        </span>
                      </div>
                    </aside>
                  </div>
                </>
              )}

              {view === "Review inbox" && (
                <section className="review-layout">
                  <aside className="review-controls">
                    <h2>Find your focus</h2>
                    <label>
                      Search promises
                      <div className="search-field">
                        <Search size={16} />
                        <input
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="Words, people, sources..."
                          aria-label="Search promises"
                        />
                      </div>
                    </label>
                    <label>
                      Status
                      <select
                        aria-label="Status"
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                      >
                        <option value="review">Needs review</option>
                        <option value="all">All promises</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="overdue">Past due</option>
                        <option value="unassigned">Owner to clarify</option>
                        <option value="complete">Complete</option>
                        <option value="rejected">Dismissed</option>
                      </select>
                    </label>
                    <div className="review-note">
                      <QuoteMark />
                      <p>
                        Read the quote.
                        <br />
                        <strong>Make your own call.</strong>
                      </p>
                      <span>
                        A matching quote shows where a suggestion came from. You
                        check what it means.
                      </span>
                    </div>
                  </aside>
                  <div className="review-results">
                    <div className="results-caption">
                      <span>
                        {filtered.length}{" "}
                        {filtered.length === 1 ? "promise" : "promises"}
                      </span>
                      <span>Evidence stays in view</span>
                    </div>
                    {filtered.length ? (
                      <div className="review-grid">
                        {filtered.map((item) => card(item))}
                      </div>
                    ) : (
                      <Empty
                        title={
                          query || filter !== "review"
                            ? "Nothing matches this view."
                            : "You're all caught up."
                        }
                        description="Try another filter, or bring in a new conversation."
                        icon={<Inbox size={28} />}
                        action={
                          <button
                            className="button secondary"
                            onClick={() => navigate("Import notes")}
                          >
                            <Plus size={15} />
                            Import notes
                          </button>
                        }
                      />
                    )}
                  </div>
                </section>
              )}

              {view === "Import notes" && (
                <div className="import-layout">
                  <section className="import-card">
                    <div className="panel-title">
                      <span className="panel-icon">
                        <FileText size={20} />
                      </span>
                      <div>
                        <h2>A place for the scattered notes.</h2>
                        <p>
                          Paste text or load a file. You'll review every
                          suggestion.
                        </p>
                      </div>
                    </div>
                    <label className="form-field">
                      Source name
                      <span>Give these notes a name you'll recognise.</span>
                      <input
                        value={sourceName}
                        onChange={(e) => setSourceName(e.target.value)}
                        maxLength={240}
                        placeholder="e.g. Research catch-up, October 21"
                        disabled={importing}
                      />
                    </label>
                    <label className="form-field timestamp-field">
                      When were these notes from?
                      <span>
                        Optional. Helps make sense of phrases like "tomorrow".
                      </span>
                      <input
                        type="datetime-local"
                        value={sourceTimestamp}
                        onChange={(e) => setSourceTimestamp(e.target.value)}
                        disabled={importing}
                      />
                    </label>
                    <label className="form-field">
                      Your notes
                      <span>
                        Only include conversations you're comfortable storing
                        here.
                      </span>
                      <textarea
                        id="import-box"
                        ref={importInput}
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder={
                          "Maya: I'll send the revised report by Friday.\n\nJon: I can share the figures tomorrow."
                        }
                        maxLength={200000}
                        disabled={importing}
                      />
                    </label>
                    <div className="notes-meta">
                      <span>{text.length.toLocaleString()} characters</span>
                      <span>
                        <LockKeyhole size={12} />
                        {remote ? "Sent to Tinker only with consent" : "Stays on this device"}
                      </span>
                    </div>
                    <label
                      className={`file-drop ${importing ? "disabled" : ""}`}
                    >
                      <Upload size={19} />
                      <span>
                        <strong>Load a text file</strong>
                        <small>.txt or .md, up to 200 KB</small>
                      </span>
                      <input
                        type="file"
                        aria-label="Choose a text file"
                        accept=".txt,.md,text/plain"
                        onChange={(e) => {
                          void loadFile(e.target.files?.[0]);
                          e.target.value = "";
                        }}
                        disabled={importing}
                      />
                    </label>
                    {remote && (
                      <>
                      {health?.research_preview && <p className="research-notice" role="note">Research preview: this checkpoint has measured regressions. Only the experiment&apos;s synthetic examples can be imported. Check every owner and date before approval.</p>}
                      <label className="remote-consent">
                        <input type="checkbox" checked={remoteConsent}
                          onChange={(e) => setRemoteConsent(e.target.checked)} disabled={importing} />
                        <span>I agree to send these notes to Thinking Machines&apos; Tinker for cloud extraction. The source and suggestions are also stored in this local workspace.</span>
                      </label>
                      </>
                    )}
                    <button
                      className="button primary full-button"
                      disabled={importing || !text.trim() || (remote && (!remoteConsent || !ready))}
                      onClick={ingest}
                    >
                      {importing ? (
                        <>
                          <LoaderCircle size={18} className="spin" />
                          Finding commitments...
                        </>
                      ) : (
                        <>
                          <Sparkles size={17} />
                          Find the promises
                          <ArrowRight size={16} />
                        </>
                      )}
                    </button>
                    {importing && (
                      <p role="status" className="processing-message">
                        {remote ? "Tinker is reading the notes." : "Your local model is reading the notes."}{" "}
                        Keep this page open; every suggestion will include its source quote.
                      </p>
                    )}
                    <p className="local-footnote">
                      <ShieldCheck size={14} />
                      {ready
                        ? remote ? `${health?.model} is configured for cloud extraction.` : `${health?.model} is ready on this device.`
                        : remote ? "A verified Tinker checkpoint must be configured to find promises." : "The local model must be running to find promises."}
                    </p>
                  </section>
                  <aside className="import-aside">
                    <div className="aside-quote">“</div>
                    <h2>
                      Keep the words.
                      <br />
                      <span>Find the promise.</span>
                    </h2>
                    <p>
                      Some things are a clear yes. Others need a bit of context.
                      The original conversation helps you tell the difference.
                    </p>
                    <div className="aside-principle">
                      <FileText size={19} />
                      <div>
                        <strong>Evidence, always</strong>
                        <p>
                          Each suggestion includes the actual words from your
                          notes.
                        </p>
                      </div>
                    </div>
                    <div className="aside-principle">
                      <CalendarDays size={19} />
                      <div>
                        <strong>Room for uncertainty</strong>
                        <p>
                          Missing people and dates can stay unresolved until you
                          check.
                        </p>
                      </div>
                    </div>
                    <div className="aside-principle">
                      <ShieldCheck size={19} />
                      <div>
                        <strong>You have the final say</strong>
                        <p>
                          Approve, edit, or dismiss. Nothing is sent
                          automatically.
                        </p>
                      </div>
                    </div>
                    <button
                      className="text-button"
                      onClick={sample}
                      disabled={importing}
                    >
                      Use clearly labelled synthetic sample notes
                      <ArrowRight size={15} />
                    </button>
                  </aside>
                </div>
              )}

              {view === "Timeline" && (
                <section className="timeline-page">
                  {timeline.length ? (
                    timeline.map(([date, entries]) => (
                      <section className="timeline-group" key={date}>
                        <div
                          className={`timeline-date ${date !== "undated" && date < localDate() ? "past-due" : ""}`}
                        >
                          <CalendarDays size={18} />
                          <div>
                            <h2>
                              {date === "undated"
                                ? "Date to clarify"
                                : dateLabel(date)}
                            </h2>
                            <span>
                              {date !== "undated" && date < localDate()
                                ? "Past due"
                                : date === "undated"
                                  ? "Confirmed, with timing still open"
                                  : "Coming up"}
                            </span>
                          </div>
                          <span className="timeline-count">
                            {entries.length}
                          </span>
                        </div>
                        <div className="timeline-cards">
                          {entries.map((item) => card(item, true))}
                        </div>
                      </section>
                    ))
                  ) : (
                    <Empty
                      title="A timeline with a little breathing room."
                      description="Approve a promise and its date will appear here. Unresolved dates have a place here too."
                      icon={<CalendarDays size={29} />}
                      action={
                        <button
                          className="button primary"
                          onClick={() => navigate("Review inbox")}
                        >
                          Open review inbox
                          <ArrowRight size={15} />
                        </button>
                      }
                    />
                  )}
                </section>
              )}
              {view === "Follow-ups" && (
                <div className="followup-layout">
                  <section className="draft-sources">
                    <div className="section-heading">
                      <div>
                        <span className="section-kicker">HUMAN APPROVED</span>
                        <h2>Ready for a nudge</h2>
                      </div>
                      <span className="count-chip">{confirmed.length}</span>
                    </div>
                    {confirmed.length ? (
                      confirmed.map((item) => (
                        <article
                          className={`follow-source ${draft?.itemId === item.id ? "active-draft-source" : ""}`}
                          key={item.id}
                        >
                          <div className="follow-source-owner">
                            <span className="person-avatar">
                              {item.owner?.slice(0, 1) || "?"}
                            </span>
                            <span>{item.owner || "Owner to clarify"}</span>
                          </div>
                          <h3>{item.claim}</h3>
                          <p className={isOverdue(item) ? "past-due" : ""}>
                            <CalendarDays size={13} />
                            {dateLabel(item.deadline)}
                          </p>
                          <button
                            className="button secondary"
                            onClick={() => makeDraft(item)}
                            disabled={busyId === item.id}
                          >
                            {busyId === item.id ? (
                              <LoaderCircle className="spin" size={14} />
                            ) : (
                              <MessageSquareText size={14} />
                            )}
                            Prepare draft
                            <ArrowRight size={14} />
                          </button>
                        </article>
                      ))
                    ) : (
                      <div className="small-empty">
                        <Inbox size={24} />
                        <h3>Start with an approved promise.</h3>
                        <p>
                          Once you've checked the evidence, you can prepare a
                          follow-up here.
                        </p>
                        <button
                          className="text-button"
                          onClick={() => navigate("Review inbox")}
                        >
                          Open review inbox
                          <ArrowRight size={14} />
                        </button>
                      </div>
                    )}
                  </section>
                  <section className="draft-editor">
                    {draft ? (
                      <>
                        <div className="editor-heading">
                          <div>
                            <span className="section-kicker">
                              YOUR WORDS, YOUR CALL
                            </span>
                            <h2>Your follow-up draft</h2>
                          </div>
                          <span className="draft-only">
                            <span />
                            Draft only
                          </span>
                        </div>
                        <label className="draft-label" htmlFor="followup-text">
                          Make it sound like you.
                        </label>
                        <textarea
                          id="followup-text"
                          value={draft.text}
                          onChange={(e) =>
                            setDraft({ ...draft, text: e.target.value })
                          }
                        />
                        <div className="draft-editor-actions">
                          <button
                            className="button primary"
                            onClick={copyDraft}
                          >
                            <Copy size={15} />
                            Copy draft
                          </button>
                          <button
                            className="button secondary"
                            onClick={() =>
                              download(
                                draft.text,
                                "follow-up-draft.txt",
                                "text/plain",
                              )
                            }
                          >
                            <ArrowDownToLine size={15} />
                            Download text
                          </button>
                        </div>
                        <div className="draft-safety">
                          <ShieldCheck size={18} />
                          <p>
                            Review the details before you send.
                            <span>
                              You choose where, when, and whether to share this
                              draft.
                            </span>
                          </p>
                        </div>
                      </>
                    ) : (
                      <div className="draft-placeholder">
                        <div className="draft-placeholder-icon">
                          <MessageSquareText size={35} />
                        </div>
                        <span className="section-kicker">
                          A CONVERSATION, NOT A CHASE
                        </span>
                        <h2>
                          The next message
                          <br />
                          starts with you.
                        </h2>
                        <p>
                          Choose an approved promise to prepare a thoughtful
                          draft. You can change every word.
                        </p>
                        <span className="private-chip">
                          <LockKeyhole size={13} />
                          No messages sent automatically
                        </span>
                      </div>
                    )}
                  </section>
                </div>
              )}

              {view === "Privacy" && (
                <div className="privacy-layout">
                  <section className="privacy-summary">
                    <div className="privacy-emblem">
                      <ShieldCheck size={34} />
                    </div>
                    <span className="eyebrow">A SPACE THAT STAYS YOURS</span>
                    <h2>
                      Your conversations
                      <br />
                      are yours.
                    </h2>
                    <p>
                      {remote ? "Notes live in your local workspace. With your consent, source text is sent to Tinker for cloud inference. Deleting it here does not delete provider-side records." : "Notes live in your local workspace. The language model runs on your computer. You choose what to keep."}
                    </p>
                    {health?.research_preview && <p>Research preview is restricted to frozen synthetic examples. This checkpoint is not approved as the production replacement.</p>}
                    <div>
                      <LockKeyhole size={17} />
                      <span>{remote ? "Cloud model account enabled" : "No cloud model account"}</span>
                    </div>
                    <div>
                      <FileText size={17} />
                      <span>Original evidence stays attached</span>
                    </div>
                    <div>
                      <CheckCheck size={17} />
                      <span>Every next step is your decision</span>
                    </div>
                  </section>
                  <div className="privacy-settings">
                    <section className="settings-card">
                      <div className="settings-icon">
                        <Leaf size={21} />
                      </div>
                      <div>
                        <h2>{remote ? "Tinker cloud model" : "Local model"}</h2>
                        <p>
                          {ready
                            ? remote ? `${health?.model} is configured. Each import requires cloud-data consent.` : `${health?.model} is installed and ready to read your notes.`
                            : remote ? "A completed, quality-checked Tinker checkpoint and credentials are required." : "The local model is unavailable. Start Ollama and check the model, then refresh."}
                        </p>
                        <span
                          className={`connection-label ${ready ? "connected" : ""}`}
                        >
                          <span className="connection-dot" />
                          {ready ? remote ? "Cloud inference configured" : "Connected on this device" : "Not connected"}
                        </span>
                      </div>
                      <button
                        className="button secondary"
                        onClick={() => refresh(true)}
                      >
                        Refresh status
                      </button>
                    </section>
                    <section className="settings-card">
                      <div className="settings-icon">
                        <ArrowDownToLine size={21} />
                      </div>
                      <div>
                        <h2>Take your promises with you</h2>
                        <p>
                          Export confirmed promises and their source quotes as a
                          CSV.
                        </p>
                        <span className="settings-detail">
                          {confirmed.length} confirmed{" "}
                          {confirmed.length === 1 ? "promise" : "promises"}{" "}
                          available
                        </span>
                      </div>
                      <button
                        className="button secondary"
                        onClick={exportConfirmed}
                        disabled={exporting}
                      >
                        {exporting ? (
                          <LoaderCircle size={15} className="spin" />
                        ) : (
                          <ArrowDownToLine size={15} />
                        )}
                        Export CSV
                      </button>
                    </section>
                    <section className="settings-card source-settings">
                      <div className="settings-icon">
                        <FolderOpen size={21} />
                      </div>
                      <div>
                        <h2>Stored source notes</h2>
                        <p>
                          Remove a source and its linked commitments and drafts.
                        </p>
                        <span className="settings-detail">
                          {sources.length}{" "}
                          {sources.length === 1 ? "source" : "sources"} stored
                          locally
                        </span>
                      </div>
                      <button
                        className="button secondary"
                        onClick={() => setManageSources((value) => !value)}
                        aria-expanded={manageSources}
                      >
                        Manage data
                      </button>
                      {manageSources && (
                        <div className="source-list">
                          {sources.length ? (
                            sources.map((source) => (
                              <div className="source-row" key={source.id}>
                                <div className="source-row-title">
                                  <FileText size={17} />
                                  <div>
                                    <strong>{source.name}</strong>
                                    <span>
                                      {source.commitments}{" "}
                                      {source.commitments === 1
                                        ? "promise"
                                        : "promises"}{" "}
                                      linked
                                    </span>
                                  </div>
                                </div>
                                {deleteId === source.id ? (
                                  <div className="delete-confirmation">
                                    <p>
                                      Delete this source and its linked data?
                                    </p>
                                    <button
                                      className="button danger"
                                      onClick={() => removeSource(source)}
                                      disabled={busyId === source.id}
                                    >
                                      {busyId === source.id ? (
                                        <LoaderCircle
                                          size={14}
                                          className="spin"
                                        />
                                      ) : (
                                        <Trash2 size={14} />
                                      )}
                                      Delete source
                                    </button>
                                    <button
                                      className="button secondary"
                                      onClick={() => setDeleteId(null)}
                                    >
                                      Keep it
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    className="button icon-button delete-source"
                                    aria-label={`Delete ${source.name}`}
                                    onClick={() => setDeleteId(source.id)}
                                  >
                                    <Trash2 size={17} />
                                  </button>
                                )}
                              </div>
                            ))
                          ) : (
                            <p className="no-sources">
                              No source notes stored. A fresh start.
                            </p>
                          )}
                        </div>
                      )}
                    </section>
                    <p className="privacy-note">
                      <ShieldCheck size={16} />
                      This is your local workspace. Back it up only somewhere
                      you trust.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
          <footer>
            <span className="footer-brand">
              <CheckCheck size={16} />
              promisekeeper
            </span>
            <span>
              A little less keeping track. A little more peace of mind.
            </span>
            <span>
              <LockKeyhole size={12} />
              {remote ? "Stored locally. Cloud AI by consent." : "Local. Private. Yours."}
            </span>
          </footer>
        </div>
      </div>
      <dialog
        ref={helpDialog}
        className="help-dialog"
        aria-labelledby="help-title"
      >
        <div className="help-dialog-heading">
          <span className="panel-icon">
            <CircleHelp size={24} />
          </span>
          <button
            className="icon-button"
            aria-label="Close help"
            onClick={() => helpDialog.current?.close()}
          >
            <X size={20} />
          </button>
        </div>
        <span className="section-kicker">A QUIETER WAY TO FOLLOW THROUGH</span>
        <h2 id="help-title">Keep the context close.</h2>
        <p>
          Import a conversation, check each suggestion beside its original
          quote, and approve the promises you want to keep track of.
        </p>
        <p>
          Confirmed promises can become editable follow-up drafts. No messages
          are sent for you. When a date or owner is unclear, you can leave it
          unresolved.
        </p>
        <div className="help-privacy">
          <ShieldCheck size={19} />
          {remote ? "Notes are stored on this device. With your explicit consent, source text is sent to Tinker for cloud extraction." : "Notes are stored on this device and processed through your local model."}
        </div>
        <button
          className="button primary full-button"
          onClick={() => helpDialog.current?.close()}
        >
          Got it
          <Check size={15} />
        </button>
      </dialog>
    </main>
  );
}

function QuoteMark() {
  return (
    <span className="large-quote" aria-hidden="true">
      “
    </span>
  );
}
function Empty({
  title,
  description,
  icon,
  action,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-symbol">{icon}</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
