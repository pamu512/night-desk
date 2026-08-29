import type { CaseStatus, Disposition } from "./types";

export function money(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function statusLabel(status: CaseStatus): string {
  return {
    open: "Unstamped",
    processing: "Working",
    hold: "HOLD",
    escalated: "ESCALATE",
  }[status];
}

export function statusClass(status: CaseStatus): string {
  return {
    open: "bg-zinc-800 text-zinc-300",
    processing: "bg-sky-950 text-sky-300",
    hold: "bg-amber-950 text-amber-200",
    escalated: "bg-orange-950 text-orange-300",
  }[status];
}

export function dispClass(d: Disposition | null): string {
  if (d === "ESCALATE") return "bg-orange-950 text-orange-300";
  if (d === "HOLD") return "bg-amber-950 text-amber-200";
  return "bg-zinc-800 text-zinc-400";
}

export function typologyLabel(t: string): string {
  return t.replaceAll("_", " ");
}
