"""ADK entrypoints for the Multi-Agent Financial Research Analyst."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from adk.agents.coordinator_agent import ADKCoordinatorAgent, ADKCoordinatorResult


def run_adk_research(
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
    """Run one coordinated research workflow through ADK wrappers."""
    return ADKCoordinatorAgent().run(
        ticker=ticker,
        company_name=company_name,
        filing_path=filing_path,
        previous_filing_path=previous_filing_path,
        peer_tickers=peer_tickers,
        include_news=include_news,
        include_filings=include_filings,
        include_peers=include_peers,
        include_thesis=include_thesis,
        session_id=session_id,
    )
