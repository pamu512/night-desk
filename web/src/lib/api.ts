import { apiBase } from "./utils";
import type { CaseRecord, Health, ShiftRecord, TraceEvent } from "./types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown = {}): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
  startShift: (goal: string, force_mock = false) =>
    post<ShiftRecord>("/api/shifts", { goal, force_mock }),
  reset: () => post<{ ok: boolean; cases: number }>("/api/reset"),
  resolve: (id: string, action: "close" | "escalate", note = "") =>
    post<CaseRecord>(`/api/cases/${id}/resolve`, { action, note }),
  eventsUrl: (shiftId: string) => `${apiBase()}/api/shifts/${shiftId}/events`,
};
