"""Coordinator Agent for multi-agent financial research workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional, Protocol, TypeVar

from agents.coordinator.models import (
    AgentExecutionMetadata,
    ConsolidatedResearchData,
    CoordinatorResponse,
    ResearchRequest,
)
from agents.filings_agent.filings_agent import FilingsAgent
from agents.filings_agent.models import FilingAgentResponse, FilingComparison
from agents.financial_agent.financial_agent import FinancialDataAgent
from agents.financial_agent.models import FinancialAnalysis
from agents.news_agent.models import NewsAgentResponse
from agents.news_agent.news_agent import NewsAgent
from agents.peer_agent.models import PeerComparisonResponse
from agents.peer_agent.peer_agent import PeerComparisonAgent
from agents.thesis_agent.models import (
    InvestmentReport,
    ThesisInput,
)
from agents.thesis_agent.thesis_agent import ThesisWriterAgent



logger = logging.getLogger(__name__)
T = TypeVar("T")


class FinancialAgentProtocol(Protocol):
    """Protocol for financial data agents."""

    def analyze_company(self, ticker: str) -> FinancialAnalysis:
        """Analyze a company ticker."""


class NewsAgentProtocol(Protocol):
    """Protocol for company news agents."""

    def analyze_news(self, company_name: str) -> NewsAgentResponse:
        """Analyze company news."""


class FilingsAgentProtocol(Protocol):
    """Protocol for filing analysis agents."""

    def analyze_filing(self, filing_path: str | Path) -> FilingAgentResponse:
        """Analyze a local filing."""

    def compare_filings(
        self,
        previous_filing_path: str | Path,
        current_filing_path: str | Path,
    ) -> FilingComparison:
        """Compare two local filings."""


class PeerAgentProtocol(Protocol):
    """Protocol for peer comparison agents."""

    def compare_peers(
        self,
        target_ticker: str,
        peer_tickers: Sequence[str] | None = None,
    ) -> PeerComparisonResponse:
        """Compare a target company with peers."""

class ThesisAgentProtocol(Protocol):
    """Protocol for thesis writer agents."""

    def generate_report(
        self,
        thesis_input: ThesisInput,
    ) -> InvestmentReport:
        """Generate an investment report."""


class CoordinatorAgent:
    """Primary orchestration entrypoint for financial research workflows."""

    def __init__(
        self,
        financial_agent: FinancialAgentProtocol | None = None,
        news_agent: NewsAgentProtocol | None = None,
        filings_agent: FilingsAgentProtocol | None = None,
        peer_agent: PeerAgentProtocol | None = None,
        thesis_agent: ThesisAgentProtocol | None = None,
    ) -> None:
        """Initialize the coordinator with injectable specialist agents."""
        self._financial_agent = financial_agent or FinancialDataAgent()
        self._news_agent = news_agent or NewsAgent()
        self._filings_agent = filings_agent or FilingsAgent()
        self._peer_agent = peer_agent or PeerComparisonAgent()
        self._thesis_agent = thesis_agent or ThesisWriterAgent()

    def generate_report(
        self,
        ticker: str,
        company_name: Optional[str] = None,
        filing_path: str | Path | None = None,
        previous_filing_path: str | Path | None = None,
        peer_tickers: Sequence[str] | None = None,
        include_news: bool = True,
        include_filings: bool = True,
        include_peers: bool = True,
        include_thesis: bool = True,
    ) -> CoordinatorResponse:
        """Run specialist agents and aggregate research outputs.

        The method continues after individual specialist failures and records
        each outcome in execution metadata.
        """
        request = ResearchRequest(
            ticker=ticker,
            company_name=company_name,
            filing_path=Path(filing_path) if filing_path is not None else None,
            previous_filing_path=Path(previous_filing_path) if previous_filing_path is not None else None,
            peer_tickers=list(peer_tickers) if peer_tickers is not None else None,
            include_news=include_news,
            include_filings=include_filings,
            include_peers=include_peers,
            include_thesis=include_thesis,
        )
        logger.info("CoordinatorAgent started request=%s", request.model_dump(mode="json"))

        metadata: list[AgentExecutionMetadata] = []
        completed_agents: list[str] = []
        failed_agents: list[str] = []
        consolidated_data = ConsolidatedResearchData()

        financial_result = self._execute_agent(
            "financial_agent",
            lambda: self._financial_agent.analyze_company(request.ticker),
            metadata,
            completed_agents,
            failed_agents,
        )
        consolidated_data.financial_analysis = financial_result

        effective_company_name = request.company_name or self._derive_company_name(request, financial_result)
        if request.include_news:
            consolidated_data.news_analysis = self._execute_agent(
                "news_agent",
                lambda: self._news_agent.analyze_news(effective_company_name),
                metadata,
                completed_agents,
                failed_agents,
            )

        if request.include_filings and request.filing_path is not None:
            consolidated_data.filing_analysis = self._execute_agent(
                "filings_agent",
                lambda: self._filings_agent.analyze_filing(request.filing_path),
                metadata,
                completed_agents,
                failed_agents,
            )
            if request.previous_filing_path is not None:
                consolidated_data.filing_comparison = self._execute_agent(
                    "filings_comparison",
                    lambda: self._filings_agent.compare_filings(
                        request.previous_filing_path,
                        request.filing_path,
                    ),
                    metadata,
                    completed_agents,
                    failed_agents,
                )

        if request.include_peers:
            consolidated_data.peer_comparison = self._execute_agent(
                "peer_agent",
                lambda: self._peer_agent.compare_peers(request.ticker, request.peer_tickers),
                metadata,
                completed_agents,
                failed_agents,
            )

        investment_report = None

        if request.include_thesis:
            try:
                thesis_input = ThesisInput(
                    company_name=effective_company_name,
                    financial_analysis=(
                        consolidated_data.financial_analysis.model_dump_json(indent=2)
                        if consolidated_data.financial_analysis
                        else "No financial analysis available."
                    ),
                    news_analysis=(
                        consolidated_data.news_analysis.model_dump_json(indent=2)
                        if consolidated_data.news_analysis
                        else None
                    ),
                    filings_analysis=(
                        consolidated_data.filing_analysis.model_dump_json(indent=2)
                        if consolidated_data.filing_analysis
                        else None
                    ),
                    peer_analysis=(
                        consolidated_data.peer_comparison.model_dump_json(indent=2)
                        if consolidated_data.peer_comparison
                        else None
                    ),
                )

                investment_report = (
                    self._thesis_agent.generate_report(
                        thesis_input
                    )
                )

                completed_agents.append(
                    "thesis_agent"
                )

            except Exception:
                failed_agents.append(
                    "thesis_agent"
                )
                logger.exception(
                    "CoordinatorAgent thesis generation failed."
                )

        response = CoordinatorResponse(
            request=request,
            consolidated_data=consolidated_data,
            execution_metadata=metadata,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
            investment_report=investment_report,
        )
        logger.info(
            "CoordinatorAgent completed completed_agents=%s failed_agents=%s",
            completed_agents,
            failed_agents,
        )
        return response

    def _execute_agent(
        self,
        agent_name: str,
        operation: Callable[[], T],
        metadata: list[AgentExecutionMetadata],
        completed_agents: list[str],
        failed_agents: list[str],
    ) -> Optional[T]:
        """Execute one specialist agent and record success or failure metadata."""
        started_at = datetime.now(UTC)
        try:
            result = operation()
        except Exception as exc:
            completed_at = datetime.now(UTC)
            failed_agents.append(agent_name)
            metadata.append(
                self._build_metadata(
                    agent_name=agent_name,
                    status="failed",
                    started_at=started_at,
                    completed_at=completed_at,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                )
            )
            logger.exception("CoordinatorAgent specialist failed agent=%s", agent_name)
            return None

        completed_at = datetime.now(UTC)
        completed_agents.append(agent_name)
        metadata.append(
            self._build_metadata(
                agent_name=agent_name,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
            )
        )
        return result

    def _build_metadata(
        self,
        agent_name: str,
        status: str,
        started_at: datetime,
        completed_at: datetime,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AgentExecutionMetadata:
        """Build execution metadata with duration in milliseconds."""
        duration_ms = (completed_at - started_at).total_seconds() * 1000
        return AgentExecutionMetadata(
            agent_name=agent_name,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message,
        )

    def _derive_company_name(
        self,
        request: ResearchRequest,
        financial_result: FinancialAnalysis | None,
    ) -> str:
        """Derive a news-search company name from financial data or ticker."""
        if request.company_name:
            return request.company_name
        if financial_result is not None:
            return financial_result.company.name
        return request.ticker


def generate_report(ticker: str) -> CoordinatorResponse:
    """Convenience function for running a coordinated research workflow."""
    return CoordinatorAgent().generate_report(ticker)