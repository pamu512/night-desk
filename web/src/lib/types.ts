export type Disposition = "AUTO_CLOSE" | "AUTO_ESCALATE" | "HUMAN_QUEUE";

export type CaseStatus =
  | "open"
  | "processing"
  | "auto_closed"
  | "auto_escalated"
  | "human_queue"
  | "resolved";

export type CaseNote = {
  summary: string;
  typology: string;
  evidence: string[];
  recommended: Disposition;
  confidence: number;
  why_human?: string | null;
};

export type CaseRecord = {
  id: string;
  typology: string;
  title: string;
  amount_usd: number;
  currency: string;
  channel: string;
  alerted_at: string;
  rule_hits: string[];
  narrative: string;
  account: Record<string, unknown>;
  payment: Record<string, unknown>;
  device: Record<string, unknown>;
  status: CaseStatus;
  note: CaseNote | null;
  agent_recommended: Disposition | null;
  final_disposition: Disposition | null;
  policy_override: boolean;
  shift_id: string | null;
};

export type TraceEvent = {
  ts: string;
  shift_id: string;
  case_id: string | null;
  agent: string;
  kind: "plan" | "tool" | "note" | "disposition" | "policy" | "info" | "error";
  message: string;
  data: Record<string, unknown>;
};

export type ShiftRecord = {
  id: string;
  goal: string;
  status: "running" | "completed" | "failed";
  started_at: string;
  finished_at: string | null;
  engine: string;
  model: string;
  pubsub_message_id: string | null;
  store_backend: string;
  counts: Record<string, number>;
  case_ids: string[];
  error: string | null;
};

export type Health = {
  ok: boolean;
  gemini: boolean;
  model: string;
  vertex: boolean;
  store: string;
  store_fallback: string | null;
  project: string;
  pubsub_topic: string;
};
