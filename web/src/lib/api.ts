import { apiBase } from "./utils";
import type { CaseRecord, Health, ShiftRecord, TraceEvent } from "./types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/api/health"),
  cases: (status?: string) =>
    get<{ cases: CaseRecord[] }>(status ? `/api/cases?status=${status}` : "/api/cases"),
  case: (id: string) => get<CaseRecord>(`/api/cases/${id}`),
  inbox: () => get<{ cases: CaseRecord[] }>("/api/inbox"),
  shifts: () => get<{ shifts: ShiftRecord[] }>("/api/shifts"),
  shift: (id: string) => get<ShiftRecord & { events: TraceEvent[] }>(`/api/shifts/${id}`),
};
