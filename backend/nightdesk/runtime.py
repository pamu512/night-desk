from __future__ import annotations

from contextvars import ContextVar

current_shift_id: ContextVar[str] = ContextVar("current_shift_id", default="")
current_case_id: ContextVar[str] = ContextVar("current_case_id", default="")
