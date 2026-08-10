from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AnalysisJob:
    id: str
    session_hash: str
    status: str = "queued"
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AnalysisJobStore:
    """In-process job ledger used locally; production persistence moves behind this same boundary."""

    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = threading.Lock()

    def create(self, session_hash: str) -> AnalysisJob:
        job = AnalysisJob(id=str(uuid.uuid4()), session_hash=session_hash)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get_for_session(self, job_id: str, session_hash: str) -> AnalysisJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job if job and job.session_hash == session_hash else None

    def emit(self, job_id: str, event: str, payload: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.events.append({"event": event, "data": payload})

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "completed"
            job.result = result
            job.events.append({"event": "completed", "data": result})

    def fail(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.error = message
            job.events.append({"event": "failed", "data": {"message": message}})

    def event_stream(self, job_id: str, session_hash: str):  # type: ignore[no-untyped-def]
        job = self.get_for_session(job_id, session_hash)
        if not job:
            return
        with self._lock:
            events = list(job.events)
        for item in events:
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"


job_store = AnalysisJobStore()
