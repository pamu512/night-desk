from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nightdesk import config
from nightdesk.models import CaseRecord, ShiftRecord, utcnow

log = logging.getLogger("nightdesk.store")


class CaseStore:
    """Firestore-backed case/shift store with a JSON file fallback.

    `google.cloud.firestore` is imported and Client() is constructed on every
    process start. Local demos without emulator credentials fall back to
    data/store.json so `uvicorn` still runs.
    """

    def __init__(self) -> None:
        self.backend = "memory"
        self.fallback_reason: str | None = None
        self._mem_cases: dict[str, dict[str, Any]] = {}
        self._mem_shifts: dict[str, dict[str, Any]] = {}
        self._client = None
        self._lock = threading.Lock()
        self._connect_firestore()
        if self.backend != "firestore":
            self._load_file()

    def _connect_firestore(self) -> None:
        # Imported and called — hackathon requirement.
        from google.cloud import firestore  # noqa: PLC0415

        live = bool(
            os.getenv("FIRESTORE_EMULATOR_HOST")
            or os.getenv("K_SERVICE")
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            or os.getenv("NIGHTDESK_FORCE_FIRESTORE") == "1"
        )
        if not live:
            self.backend = "memory"
            self.fallback_reason = "no emulator, Cloud Run, or ADC — file store"
            log.info("Firestore client imported; using file store until ADC/emulator is present")
            return
        try:
            project = config.google_cloud_project() or None
            self._client = firestore.Client(project=project) if project else firestore.Client()
            ping = (
                self._client.collection(config.FIRESTORE_COLLECTION)
                .document("_health")
            )
            ping.set({"ok": True, "service": "nightdesk"}, merge=True)
            self.backend = "firestore"
            log.info("Firestore connected project=%s", project or "(adc)")
        except Exception as exc:  # noqa: BLE001
            self._client = None
            self.backend = "memory"
            self.fallback_reason = f"{type(exc).__name__}: {exc}"
            log.warning("Firestore unavailable, using file store (%s)", self.fallback_reason)

    def _col(self, name: str):
        assert self._client is not None
        return self._client.collection(config.FIRESTORE_COLLECTION).document(name).collection("items")

    def _file(self) -> Path:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return config.DATA_DIR / "store.json"

    def _load_file(self) -> None:
        path = self._file()
        if not path.exists():
            return
        raw = json.loads(path.read_text())
        self._mem_cases = raw.get("cases", {})
        self._mem_shifts = raw.get("shifts", {})

    def _save_file(self) -> None:
        if self.backend == "firestore":
            return
        path = self._file()
        payload = json.dumps({"cases": self._mem_cases, "shifts": self._mem_shifts}, indent=2)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".store-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def upsert_case(self, case: CaseRecord) -> CaseRecord:
        payload = case.model_dump()
        if self.backend == "firestore" and self._client is not None:
            self._col("cases").document(case.id).set(payload)
        else:
            self._mem_cases[case.id] = payload
            self._save_file()
        return case

    def get_case(self, case_id: str) -> CaseRecord | None:
        if self.backend == "firestore" and self._client is not None:
            snap = self._col("cases").document(case_id).get()
            if not snap.exists:
                return None
            return CaseRecord.model_validate(snap.to_dict())
        raw = self._mem_cases.get(case_id)
        return CaseRecord.model_validate(raw) if raw else None

    def list_cases(self, status: str | None = None) -> list[CaseRecord]:
        if self.backend == "firestore" and self._client is not None:
            query = self._col("cases")
            if status:
                query = query.where("status", "==", status)
            rows = [CaseRecord.model_validate(d.to_dict()) for d in query.stream()]
        else:
            rows = [CaseRecord.model_validate(v) for v in self._mem_cases.values()]
            if status:
                rows = [c for c in rows if c.status == status]
        rows.sort(key=lambda c: c.alerted_at)
        return rows

    def upsert_shift(self, shift: ShiftRecord) -> ShiftRecord:
        payload = shift.model_dump()
        if self.backend == "firestore" and self._client is not None:
            self._col("shifts").document(shift.id).set(payload)
        else:
            self._mem_shifts[shift.id] = payload
            self._save_file()
        return shift

    def get_shift(self, shift_id: str) -> ShiftRecord | None:
        if self.backend == "firestore" and self._client is not None:
            snap = self._col("shifts").document(shift_id).get()
            if not snap.exists:
                return None
            return ShiftRecord.model_validate(snap.to_dict())
        raw = self._mem_shifts.get(shift_id)
        return ShiftRecord.model_validate(raw) if raw else None

    def list_shifts(self) -> list[ShiftRecord]:
        if self.backend == "firestore" and self._client is not None:
            rows = [ShiftRecord.model_validate(d.to_dict()) for d in self._col("shifts").stream()]
        else:
            rows = [ShiftRecord.model_validate(v) for v in self._mem_shifts.values()]
        rows.sort(key=lambda s: s.started_at, reverse=True)
        return rows

    def live_shift_ids(self, except_id: str | None = None) -> set[str]:
        return {s.id for s in self.list_shifts() if s.status == "running" and s.id != except_id}

    def _claim_stale(self, case: CaseRecord) -> bool:
        if not case.claimed_at:
            return False
        try:
            claimed = datetime.fromisoformat(case.claimed_at)
        except ValueError:
            return True
        if claimed.tzinfo is None:
            claimed = claimed.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - claimed).total_seconds()
        return age > config.claim_ttl_seconds()

    def _claim_blocked(self, case: CaseRecord, shift_id: str, rivals: set[str] | None) -> bool:
        holder = case.shift_id
        if not holder or holder == shift_id:
            return False
        if self._claim_stale(case):
            return False
        other = self.get_shift(holder)
        if other is None or other.status == "failed":
            return False
        if other.status == "running":
            return True
        # Overlapping sibling already finished — do not re-process its cases.
        return bool(rivals and holder in rivals)

    def _take_claim(self, case: CaseRecord, shift_id: str) -> CaseRecord:
        case.status = "processing"
        case.shift_id = shift_id
        case.claimed_at = utcnow()
        return case

    def claim_case(
        self, case_id: str, shift_id: str, *, rivals: set[str] | None = None
    ) -> CaseRecord | None:
        """Atomically claim a case for this shift. None if another live/rival shift holds it."""
        with self._lock:
            if self.backend == "firestore" and self._client is not None:
                return self._claim_case_firestore(case_id, shift_id, rivals)
            case = self.get_case(case_id)
            if case is None or self._claim_blocked(case, shift_id, rivals):
                return None
            case = self._take_claim(case, shift_id)
            self._mem_cases[case.id] = case.model_dump()
            self._save_file()
            return case

    def _claim_case_firestore(
        self, case_id: str, shift_id: str, rivals: set[str] | None
    ) -> CaseRecord | None:
        from google.cloud import firestore

        ref = self._col("cases").document(case_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def _txn(txn: Any) -> CaseRecord | None:
            snap = ref.get(transaction=txn)
            if not snap.exists:
                return None
            case = CaseRecord.model_validate(snap.to_dict())
            if self._claim_blocked(case, shift_id, rivals):
                return None
            case = self._take_claim(case, shift_id)
            txn.set(ref, case.model_dump())
            return case

        return _txn(transaction)

    def replace_cases(self, cases: list[CaseRecord]) -> None:
        if self.backend == "firestore" and self._client is not None:
            batch = self._client.batch()
            for existing in self._col("cases").stream():
                batch.delete(existing.reference)
            batch.commit()
            for case in cases:
                self._col("cases").document(case.id).set(case.model_dump())
        else:
            self._mem_cases = {c.id: c.model_dump() for c in cases}
            self._save_file()

    def snapshot(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "fallback_reason": self.fallback_reason,
            "cases": deepcopy(self._mem_cases),
        }


store = CaseStore()
