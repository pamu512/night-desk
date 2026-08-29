from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

Disposition = Literal["AUTO_CLOSE", "AUTO_ESCALATE", "HUMAN_QUEUE"]
CaseStatus = Literal[
    "open",
    "processing",
    "auto_closed",
    "auto_escalated",
    "human_queue",
    "resolved",
]
ShiftStatus = Literal["running", "completed", "failed"]


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class CaseNote(BaseModel):
    summary: str
    typology: str
    evidence: list[str] = Field(default_factory=list)
    recommended: Disposition
    confidence: float = 0.5
    why_human: str | None = None


class CaseRecord(BaseModel):
    id: str
    typology: str
    title: str
    amount_usd: float
    currency: str = "USD"
    channel: str = "app"
    alerted_at: str
    rule_hits: list[str] = Field(default_factory=list)
    narrative: str
    account: dict[str, Any] = Field(default_factory=dict)
    payment: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    refunds_7d: list[dict[str, Any]] = Field(default_factory=list)
    loyalty: dict[str, Any] | None = None
    velocity: dict[str, Any] | None = None
    delivery: dict[str, Any] | None = None
    travel: dict[str, Any] | None = None
    ato: dict[str, Any] | None = None
    household: dict[str, Any] | None = None
    network_labels: list[str] = Field(default_factory=list)
    status: CaseStatus = "open"
    note: CaseNote | None = None
    agent_recommended: Disposition | None = None
    final_disposition: Disposition | None = None
    policy_override: bool = False
    shift_id: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None


class TraceEvent(BaseModel):
    ts: str
    shift_id: str
    case_id: str | None = None
    agent: str
    kind: Literal["plan", "tool", "note", "disposition", "policy", "info", "error"]
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class ShiftRecord(BaseModel):
    id: str
    goal: str
    status: ShiftStatus = "running"
    started_at: str
    finished_at: str | None = None
    engine: str
    model: str
    pubsub_message_id: str | None = None
    store_backend: str = "memory"
    counts: dict[str, int] = Field(default_factory=dict)
    case_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class Facts(BaseModel):
    """Normalized facts the policy guard reads. Built from tool output, not the LLM."""

    case_id: str
    amount_usd: float
    account_age_days: int
    prior_fraud_cases: int
    chargebacks_90d: int
    refund_count_7d: int
    same_device_accounts: int
    welcome_bonuses: int
    referrals_14d: int
    auth_fails_15m: int
    unique_bins_15m: int
    ato_signals: bool
    inr_with_delivery_proof: bool
    travel_consistent: bool
    household_ambiguous: bool
    card_testing: bool
    typology: str
