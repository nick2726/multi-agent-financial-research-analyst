"""Session persistence primitives for ADK-style orchestration."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field


class SessionRunRecord(BaseModel):
    """One coordinated run stored under a session."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request: dict[str, Any]
    completed_agents: list[str]
    failed_agents: list[str]
    has_failures: bool


class SessionRecord(BaseModel):
    """Persistent ADK session containing many coordinator runs."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    runs: list[SessionRunRecord] = Field(default_factory=list)


class SessionStore(Protocol):
    """Protocol for ADK session persistence implementations."""

    def get_or_create(self, session_id: str | None = None) -> SessionRecord:
        """Get an existing session or create a new one."""

    def append_run(self, session_id: str, run: SessionRunRecord) -> SessionRecord:
        """Persist one run under a session."""


class FileSessionStore:
    """Simple JSON file-backed session store for local ADK development."""

    def __init__(self, store_path: str | Path = "adk/sessions/data/sessions.json") -> None:
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def get_or_create(self, session_id: str | None = None) -> SessionRecord:
        sessions = self._load_all()
        if session_id and session_id in sessions:
            return SessionRecord.model_validate(sessions[session_id])

        record = SessionRecord(session_id=session_id or str(uuid.uuid4()))
        sessions[record.session_id] = record.model_dump(mode="json")
        self._save_all(sessions)
        return record

    def append_run(self, session_id: str, run: SessionRunRecord) -> SessionRecord:
        sessions = self._load_all()
        if session_id not in sessions:
            sessions[session_id] = SessionRecord(session_id=session_id).model_dump(mode="json")

        record = SessionRecord.model_validate(sessions[session_id])
        record.runs.append(run)
        record.updated_at = datetime.now(UTC)
        sessions[session_id] = record.model_dump(mode="json")
        self._save_all(sessions)
        return record

    def _load_all(self) -> dict[str, Any]:
        if not self._store_path.exists():
            return {}
        with self._store_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_all(self, sessions: dict[str, Any]) -> None:
        with self._store_path.open("w", encoding="utf-8") as handle:
            json.dump(sessions, handle, indent=2)
