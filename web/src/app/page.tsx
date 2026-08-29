"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { dispClass, money, statusClass, statusLabel, typologyLabel } from "@/lib/labels";
import type { CaseRecord, Health, ShiftRecord, TraceEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const DEFAULT_GOAL =
  "Clear the overnight refund, loyalty, and payment-abuse queue. Write a case note on every open case. Queue only the real decisions for a human.";

function kindColor(kind: TraceEvent["kind"]): string {
  return (
    {
      plan: "text-sky-300",
      tool: "text-zinc-300",
      note: "text-lime-300",
      disposition: "text-amber-200",
      policy: "text-violet-300",
      info: "text-zinc-400",
      error: "text-orange-400",
    }[kind] || "text-zinc-400"
  );
}

export default function DeskPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [goal, setGoal] = useState(DEFAULT_GOAL);
  const [running, setRunning] = useState(false);
  const [shift, setShift] = useState<ShiftRecord | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<"inbox" | "all">("all");
  const [busy, setBusy] = useState(false);
  const [resolveNote, setResolveNote] = useState("");
  const traceRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(async () => {
    try {
      const [h, c] = await Promise.all([api.health(), api.cases()]);
      setHealth(h);
      setHealthError(null);
      setCases(c.cases);
    } catch (err) {
      setHealthError(err instanceof Error ? err.message : "API unreachable");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 2500);
    return () => clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    if (traceRef.current) {
      traceRef.current.scrollTop = traceRef.current.scrollHeight;
    }
  }, [events]);

  const selected = useMemo(
    () => cases.find((c) => c.id === selectedId) || null,
    [cases, selectedId],
  );

  const counts = useMemo(() => {
    const by = (s: CaseRecord["status"]) => cases.filter((c) => c.status === s).length;
    return {
      open: by("open"),
      human: by("human_queue"),
      closed: by("auto_closed"),
      escalated: by("auto_escalated"),
      resolved: by("resolved"),
    };
  }, [cases]);

  const visible = cases.filter((c) => (tab === "inbox" ? c.status === "human_queue" : true));

  async function startShift() {
    setBusy(true);
    setEvents([]);
    setRunning(true);
    try {
      const started = await api.startShift(goal, !health?.gemini);
      setShift(started);
      const es = new EventSource(api.eventsUrl(started.id));
      es.onmessage = (msg) => {
        const ev = JSON.parse(msg.data) as TraceEvent;
        setEvents((prev) => [...prev, ev]);
      };
      es.addEventListener("done", () => {
        es.close();
        setRunning(false);
        void refresh();
        void api.shift(started.id).then(setShift);
      });
      es.onerror = () => {
        es.close();
        setRunning(false);
        void refresh();
      };
    } catch (err) {
      setRunning(false);
      setHealthError(err instanceof Error ? err.message : "shift failed");
    } finally {
      setBusy(false);
    }
  }

  async function resetQueue() {
    setBusy(true);
    try {
      await api.reset();
      setEvents([]);
      setShift(null);
      setSelectedId(null);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function resolve(action: "close" | "escalate") {
    if (!selected) return;
    setBusy(true);
    try {
      await api.resolve(selected.id, action, resolveNote);
      setResolveNote("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-4 py-3 md:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-[0.2em] text-lime-300">
              Night Desk
            </span>
            <Badge className="bg-zinc-800 text-zinc-400">Taskmaster</Badge>
          </div>
          <p className="mt-0.5 text-sm text-zinc-400">
            Meridian Wallet · overnight refund / loyalty / payment-abuse queue
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {healthError && (
            <Badge className="bg-orange-950 text-orange-300">API: {healthError}</Badge>
          )}
          {health && (
            <>
              <Badge className={health.gemini ? "bg-lime-950 text-lime-300" : "bg-zinc-800 text-zinc-400"}>
                {health.gemini ? `Gemini ${health.model}` : "Planner (no Gemini key)"}
              </Badge>
              <Badge className="bg-zinc-800 text-zinc-400">
                store {health.store}
              </Badge>
              <Badge className="bg-zinc-800 text-zinc-400">
                {health.project}
              </Badge>
            </>
          )}
        </div>
      </header>

      <main className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-12 lg:p-6">
        <section className="flex flex-col gap-4 lg:col-span-4">
          <Card className="p-4">
            <p className="text-xs font-mono uppercase tracking-widest text-zinc-500">
              Goal
            </p>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={4}
              className="mt-2 w-full resize-none rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm leading-relaxed text-zinc-200 outline-none focus:border-lime-400"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={() => void startShift()} disabled={busy || running || counts.open === 0}>
                {running ? "Working the queue…" : "Run night shift"}
              </Button>
              <Button variant="outline" onClick={() => void resetQueue()} disabled={busy || running}>
                Reseed sample cases
              </Button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-zinc-500">
              The agent plans, pulls device/loyalty/velocity context, writes a
              case note, then a policy guard decides. Only ambiguous or
              high-value cases land in the human inbox.
            </p>
          </Card>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2">
            <Stat label="Open" value={counts.open} hint="still in queue" />
            <Stat label="Human inbox" value={counts.human} hint="your morning list" accent />
            <Stat label="Auto-closed" value={counts.closed} hint="benign" />
            <Stat label="Auto-escalated" value={counts.escalated} hint="confirmed abuse" />
          </div>

          <Card className="flex min-h-[280px] flex-1 flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
              <p className="text-xs font-mono uppercase tracking-widest text-zinc-500">
                Agent trace
              </p>
              {shift && (
                <span className="font-mono text-[11px] text-zinc-500">
                  {shift.id} · {shift.engine}
                </span>
              )}
            </div>
            <div ref={traceRef} className="flex-1 overflow-y-auto px-4 py-3">
              {events.length === 0 ? (
                <p className="text-sm text-zinc-500">
                  {healthError
                    ? "Start the API (`python -m nightdesk`) and refresh."
                    : "Idle. Run a night shift to watch the agent work the queue."}
                </p>
              ) : (
                <ol className="space-y-2">
                  {events.map((ev, i) => (
                    <li key={`${ev.ts}-${i}`} className="font-mono text-[11px] leading-snug">
                      <span className="text-zinc-600">{ev.ts.slice(11, 19)}</span>{" "}
                      <span className="text-zinc-500">{ev.agent}</span>{" "}
                      <span className={kindColor(ev.kind)}>{ev.message}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </Card>
        </section>

        <section className="flex flex-col gap-4 lg:col-span-8">
          <div className="flex items-center gap-2">
            <Button
              variant={tab === "all" ? "default" : "ghost"}
              onClick={() => setTab("all")}
            >
              All cases ({cases.length})
            </Button>
            <Button
              variant={tab === "inbox" ? "default" : "ghost"}
              onClick={() => setTab("inbox")}
            >
              Human inbox ({counts.human})
            </Button>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="overflow-hidden">
              {visible.length === 0 ? (
                <div className="p-6 text-sm text-zinc-500">
                  {tab === "inbox"
                    ? "Inbox empty. Either the shift has not run, or every case was auto-acted."
                    : "No cases. Reseed the sample queue."}
                </div>
              ) : (
                <ul className="divide-y divide-zinc-800">
                  {visible.map((c) => (
                    <li key={c.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(c.id)}
                        className={`flex w-full flex-col gap-1 px-4 py-3 text-left hover:bg-zinc-800/60 ${
                          selectedId === c.id ? "bg-zinc-800/80" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs text-zinc-500">{c.id}</span>
                          <Badge className={statusClass(c.status)}>{statusLabel(c.status)}</Badge>
                        </div>
                        <p className="text-sm text-zinc-100">{c.title}</p>
                        <p className="text-xs text-zinc-500">
                          {money(c.amount_usd)} · {typologyLabel(c.typology)}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="p-4">
              {!selected ? (
                <p className="text-sm text-zinc-500">
                  Select a case. After a shift, open the human inbox — those
                  two are the only decisions that should have reached you.
                </p>
              ) : (
                <CaseDetail
                  case={selected}
                  resolveNote={resolveNote}
                  setResolveNote={setResolveNote}
                  onResolve={resolve}
                  busy={busy}
                />
              )}
            </Card>
          </div>
        </section>
      </main>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: number;
  hint: string;
  accent?: boolean;
}) {
  return (
    <Card className="p-3">
      <p className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</p>
      <p className={`mt-1 font-mono text-2xl ${accent ? "text-amber-200" : "text-zinc-100"}`}>
        {value}
      </p>
      <p className="text-[11px] text-zinc-600">{hint}</p>
    </Card>
  );
}

function CaseDetail({
  case: c,
  resolveNote,
  setResolveNote,
  onResolve,
  busy,
}: {
  case: CaseRecord;
  resolveNote: string;
  setResolveNote: (v: string) => void;
  onResolve: (a: "close" | "escalate") => void;
  busy: boolean;
}) {
  const account = c.account as { email?: string; age_days?: number; loyalty_tier?: string };
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-zinc-500">{c.id}</span>
        <Badge className={statusClass(c.status)}>{statusLabel(c.status)}</Badge>
        {c.final_disposition && (
          <Badge className={dispClass(c.final_disposition)}>{c.final_disposition}</Badge>
        )}
        {c.policy_override && (
          <Badge className="bg-violet-950 text-violet-200">policy override</Badge>
        )}
      </div>
      <h2 className="text-lg font-medium leading-snug">{c.title}</h2>
      <p className="text-sm text-zinc-400">{c.narrative}</p>
      <p className="text-xs text-zinc-500">
        {money(c.amount_usd)} · {c.channel} · {account.email} · tenure {account.age_days}d ·{" "}
        {account.loyalty_tier}
      </p>
      <div className="flex flex-wrap gap-1">
        {c.rule_hits.map((h) => (
          <Badge key={h} className="bg-zinc-800 text-zinc-400">
            {h}
          </Badge>
        ))}
      </div>
      {c.note ? (
        <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs font-mono uppercase tracking-widest text-lime-300">
            Case note
          </p>
          <p className="mt-2 text-sm leading-relaxed text-zinc-200">{c.note.summary}</p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-zinc-400">
            {c.note.evidence.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
          {c.note.why_human && (
            <p className="mt-2 text-xs text-amber-200">Why human: {c.note.why_human}</p>
          )}
          <p className="mt-2 font-mono text-[11px] text-zinc-600">
            agent {c.agent_recommended} · confidence {c.note.confidence.toFixed(2)}
          </p>
        </div>
      ) : (
        <p className="text-sm text-zinc-500">No note yet — run the night shift.</p>
      )}
      {c.status === "human_queue" && (
        <div className="space-y-2 border-t border-zinc-800 pt-3">
          <textarea
            value={resolveNote}
            onChange={(e) => setResolveNote(e.target.value)}
            placeholder="Optional analyst addendum"
            rows={2}
            className="w-full resize-none rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400"
          />
          <div className="flex gap-2">
            <Button variant="outline" disabled={busy} onClick={() => onResolve("close")}>
              Close as benign
            </Button>
            <Button variant="danger" disabled={busy} onClick={() => onResolve("escalate")}>
              Escalate
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
