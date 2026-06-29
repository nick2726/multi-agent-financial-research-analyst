"""ADK coordinator wrapper over the existing custom coordinator agent."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from adk.sessions.session_store import FileSessionStore, SessionRunRecord, SessionStore
from agents.coordinator.coordinator_agent import CoordinatorAgent
from agents.coordinator.models import CoordinatorResponse


class CoordinatorService(Protocol):
    """Protocol for the wrapped coordinator implementation."""

    def generate_report(
        self,
        ticker: str,
        company_name: str | None = None,
        filing_path: str | Path | None = None,
        previous_filing_path: str | Path | None = None,
        peer_tickers: Sequence[str] | None = None,
        include_news: bool = True,
        include_filings: bool = True,
        include_peers: bool = True,
        include_thesis: bool = True,
    ) -> CoordinatorResponse:
        """Generate unified coordinator response for a research request."""


class ADKCoordinatorResult(BaseModel):
    """Result envelope produced by ADK coordinator wrapper."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    coordinator_response: CoordinatorResponse
    run_id: str


class ADKCoordinatorAgent:
    """ADK-ready coordinator that reuses existing orchestration logic as-is."""

    def __init__(
        self,
        coordinator: CoordinatorService | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        self._coordinator = coordinator or CoordinatorAgent()
        self._session_store = session_store or FileSessionStore()

    def run(
        self,
        ticker: str,
        company_name: str | None = None,
        filing_path: str | Path | None = None,
        previous_filing_path: str | Path | None = None,
        peer_tickers: Sequence[str] | None = None,
        include_news: bool = True,
        include_filings: bool = True,
        include_peers: bool = True,
        include_thesis: bool = True,
        session_id: str | None = None,
    ) -> ADKCoordinatorResult:
        """Execute one ADK coordinator run and persist structured session history."""
        session = self._session_store.get_or_create(session_id)

        response = self._coordinator.generate_report(
            ticker=ticker,
            company_name=company_name,
            filing_path=filing_path,
            previous_filing_path=previous_filing_path,
            peer_tickers=peer_tickers,
            include_news=include_news,
            include_filings=include_filings,
            include_peers=include_peers,
            include_thesis=include_thesis,
        )

        run_record = SessionRunRecord(
            request=response.request.model_dump(mode="json"),
            completed_agents=response.completed_agents,
            failed_agents=response.failed_agents,
            has_failures=response.has_failures,
            response_snapshot=response.model_dump(mode="json"),
        )
        self._session_store.append_run(session.session_id, run_record)

        return ADKCoordinatorResult(
            session_id=session.session_id,
            coordinator_response=response,
            run_id=run_record.run_id,
        )
