"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { dispClass, money, statusClass, statusLabel, typologyLabel } from "@/lib/labels";
import type { CaseRecord, Health, ShiftRecord, TraceEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const DEFAULT_GOAL =
  "Stamp a hold receipt on every case. Escalate only slam-dunk abuse when Gemini/Vertex and Pub/Sub are up. Never close money.";

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
  const [busy, setBusy] = useState(false);
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

  const unstamped = cases.filter((c) => c.status === "open").length;
  const holds = cases.filter((c) => c.final_disposition === "HOLD").length;
  const escalated = cases.filter((c) => c.final_disposition === "ESCALATE").length;

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

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-4 py-3 md:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-[0.2em] text-lime-300">
              Night Desk
            </span>
            <Badge className="bg-zinc-800 text-zinc-400">HOLD / ESCALATE</Badge>
          </div>
          <p className="mt-0.5 text-sm text-zinc-400">
            Hold receipts for refund, loyalty, and payment-abuse review
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {healthError && (
            <Badge className="bg-orange-950 text-orange-300">API: {healthError}</Badge>
          )}
          {health?.rails && (
            <>
              {(health.rails.present.length ? health.rails.present : []).map((r) => (
                <Badge key={r} className="bg-lime-950 text-lime-300">
                  {r} present
                </Badge>
              ))}
              {health.rails.missing.map((r) => (
                <Badge key={r} className="bg-amber-950 text-amber-200">
                  {r} missing
                </Badge>
              ))}
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
              <Button onClick={() => void startShift()} disabled={busy || running || unstamped === 0}>
                {running ? "Stamping receipts…" : "Stamp receipts"}
              </Button>
              <Button variant="outline" onClick={() => void resetQueue()} disabled={busy || running}>
                Reseed sample cases
              </Button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-zinc-500">
              Gemini writes the note. <code>decide()</code> stamps HOLD or
              ESCALATE. Missing Gemini, Vertex, or Pub/Sub fails closed to HOLD.
              Nothing leaves this list. Money is never closed unattended.
            </p>
          </Card>

          <div className="grid grid-cols-2 gap-2">
            <Stat label="HOLD" value={holds} hint="receipts that stay" accent />
            <Stat label="ESCALATE" value={escalated} hint="slam-dunk only" />
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
                    : "Idle. Stamp receipts to watch the guard hold."}
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
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-500">
            Hold receipts · {cases.length} stay put
          </p>
          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="overflow-hidden">
              {cases.length === 0 ? (
                <div className="p-6 text-sm text-zinc-500">No cases. Reseed the sample queue.</div>
              ) : (
                <ul className="divide-y divide-zinc-800">
                  {cases.map((c) => (
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
                          <Badge className={c.final_disposition ? dispClass(c.final_disposition) : statusClass(c.status)}>
                            {c.final_disposition || statusLabel(c.status)}
                          </Badge>
                        </div>
                        <p className="text-sm text-zinc-100">{c.title}</p>
                        {c.note ? (
                          <>
                            <p className="text-xs text-amber-200">{c.note.why_human}</p>
                            <p className="text-[11px] text-zinc-500">
                              present {c.note.present.join(", ") || "—"} · missing{" "}
                              {c.note.missing.join(", ") || "—"}
                            </p>
                          </>
                        ) : (
                          <p className="text-xs text-zinc-500">
                            {money(c.amount_usd)} · {typologyLabel(c.typology)}
                          </p>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="p-4">
              {!selected ? (
                <p className="text-sm text-zinc-500">
                  First-open is a HOLD that stays. Open a row for the stamped
                  receipt — why, present, missing. Gemini never AUTO_CLOSE.
                </p>
              ) : (
                <ReceiptDetail case={selected} />
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

function ReceiptDetail({ case: c }: { case: CaseRecord }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-zinc-500">{c.id}</span>
        {c.final_disposition && (
          <Badge className={dispClass(c.final_disposition)}>{c.final_disposition}</Badge>
        )}
        {c.note?.override && (
          <Badge className="bg-violet-950 text-violet-200">guard overrode Gemini</Badge>
        )}
      </div>
      <h2 className="text-lg font-medium leading-snug">{c.title}</h2>
      <p className="text-xs text-zinc-500">
        {money(c.amount_usd)} · {typologyLabel(c.typology)}
      </p>
      {c.note ? (
        <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs font-mono uppercase tracking-widest text-lime-300">
            Receipt
          </p>
          <p className="mt-2 text-sm leading-relaxed text-zinc-200">{c.note.summary}</p>
          <p className="mt-2 text-xs text-amber-200">Why: {c.note.why_human}</p>
          <p className="mt-2 text-xs text-zinc-400">
            present: {c.note.present.join(", ") || "—"}
          </p>
          <p className="text-xs text-zinc-500">
            missing: {c.note.missing.join(", ") || "—"}
          </p>
          {c.note.evidence.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-zinc-400">
              {c.note.evidence.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          )}
          {c.note.override && c.note.gemini_recommended && (
            <p className="mt-2 font-mono text-[11px] text-violet-300">
              Gemini drafted {c.note.gemini_recommended}; decide() kept{" "}
              {c.note.recommended}.
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm text-zinc-500">No receipt yet — stamp the shift.</p>
      )}
    </div>
  );
}
