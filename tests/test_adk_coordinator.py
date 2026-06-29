"""Tests for ADK coordinator wrappers and session persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from adk.agents.coordinator_agent import ADKCoordinatorAgent
from adk.sessions.session_store import FileSessionStore
from agents.coordinator.models import (
    AgentExecutionMetadata,
    ConsolidatedResearchData,
    CoordinatorResponse,
    ResearchRequest,
)


class FakeCoordinatorService:
    """Fake coordinator for ADK wrapper tests."""

    def generate_report(
        self,
        ticker: str,
        company_name: str | None = None,
        filing_path: str | Path | None = None,
        previous_filing_path: str | Path | None = None,
        peer_tickers: list[str] | None = None,
        include_news: bool = True,
        include_filings: bool = True,
        include_peers: bool = True,
        include_thesis: bool = True,
    ) -> CoordinatorResponse:
        """Return deterministic coordinator response."""
        request = ResearchRequest(
            ticker=ticker,
            company_name=company_name,
            filing_path=Path(filing_path) if filing_path else None,
            previous_filing_path=Path(previous_filing_path) if previous_filing_path else None,
            peer_tickers=peer_tickers,
            include_news=include_news,
            include_filings=include_filings,
            include_peers=include_peers,
            include_thesis=include_thesis,
        )
        return CoordinatorResponse(
            request=request,
            consolidated_data=ConsolidatedResearchData(),
            execution_metadata=[
                AgentExecutionMetadata(
                    agent_name="financial_agent",
                    status="completed",
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                    duration_ms=1.2,
                )
            ],
            completed_agents=["financial_agent"],
            failed_agents=[],
        )


def test_adk_coordinator_persists_runs(tmp_path: Path) -> None:
    """ADK coordinator should persist run history in session store."""
    store_path = tmp_path / "sessions.json"
    adk_agent = ADKCoordinatorAgent(
        coordinator=FakeCoordinatorService(),
        session_store=FileSessionStore(store_path),
    )

    first = adk_agent.run("INFY.NS")
    second = adk_agent.run("INFY.NS", session_id=first.session_id)

    assert first.session_id == second.session_id
    sessions = FileSessionStore(store_path).get_or_create(first.session_id)
    assert len(sessions.runs) == 2
    assert sessions.runs[0].request["ticker"] == "INFY.NS"
