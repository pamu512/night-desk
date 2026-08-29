import type { CaseStatus, Disposition } from "./types";

export function money(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function statusLabel(status: CaseStatus): string {
  return {
    open: "Open",
    processing: "Working",
    auto_closed: "Auto-closed",
    auto_escalated: "Auto-escalated",
    human_queue: "Needs human",
    resolved: "Resolved",
  }[status];
}

export function statusClass(status: CaseStatus): string {
  return {
    open: "bg-zinc-800 text-zinc-300",
    processing: "bg-sky-950 text-sky-300",
    auto_closed: "bg-emerald-950 text-emerald-300",
    auto_escalated: "bg-orange-950 text-orange-300",
    human_queue: "bg-amber-950 text-amber-200",
    resolved: "bg-zinc-800 text-zinc-400",
  }[status];
}

export function dispClass(d: Disposition | null): string {
  if (d === "AUTO_CLOSE") return "bg-emerald-950 text-emerald-300";
  if (d === "AUTO_ESCALATE") return "bg-orange-950 text-orange-300";
  if (d === "HUMAN_QUEUE") return "bg-amber-950 text-amber-200";
  return "bg-zinc-800 text-zinc-400";
}

export function typologyLabel(t: string): string {
  return t.replaceAll("_", " ");
}
