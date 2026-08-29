"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { dispClass, money, statusClass, statusLabel, typologyLabel } from "@/lib/labels";
import type { CaseRecord, Health } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export default function DeskPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

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

  const selected = useMemo(
    () => cases.find((c) => c.id === selectedId) || null,
    [cases, selectedId],
  );

  const holds = cases.filter((c) => c.final_disposition === "HOLD").length;
  const escalated = cases.filter((c) => c.final_disposition === "ESCALATE").length;

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
          {health && !health.shifts?.enabled && (
            <Badge className="bg-zinc-800 text-zinc-400">live shifts off</Badge>
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
              First-open
            </p>
            <p className="mt-2 text-sm leading-relaxed text-zinc-200">
              Seeded hold receipts. Why and present/missing are already on each
              row. This page does not start a live shift and does not call Vertex.
            </p>
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
        </section>

        <section className="flex flex-col gap-4 lg:col-span-8">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-500">
            Hold receipts · {cases.length} stay put
          </p>
          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="overflow-hidden">
              {healthError && cases.length === 0 ? (
                <div className="p-6 text-sm text-zinc-500">
                  API unreachable. Start it with <code>python -m nightdesk</code>.
                </div>
              ) : cases.length === 0 ? (
                <div className="p-6 text-sm text-zinc-500">Loading seeded receipts…</div>
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
        <p className="text-sm text-zinc-500">No receipt yet — seed is still loading.</p>
      )}
    </div>
  );
}
