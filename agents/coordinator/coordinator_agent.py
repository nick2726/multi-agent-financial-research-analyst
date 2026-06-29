"""Coordinator Agent orchestrating specialist financial research agents."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, Protocol, TypeVar

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
from agents.thesis_agent.models import InvestmentReport, ThesisInput
from agents.thesis_agent.thesis_agent import ThesisWriterAgent

logger = logging.getLogger(__name__)
T = TypeVar("T")


class FinancialAgentProtocol(Protocol):
    """Protocol for a financial specialist agent."""

    def analyze_company(self, ticker: str) -> FinancialAnalysis:
        """Return financial analysis for a ticker."""


class NewsAgentProtocol(Protocol):
    """Protocol for a news specialist agent."""

    def analyze_news(self, company_name: str) -> NewsAgentResponse:
        """Return news analysis for a company."""


class FilingsAgentProtocol(Protocol):
    """Protocol for a filings specialist agent."""

    def analyze_filing(self, filing_path: str | Path) -> FilingAgentResponse:
        """Analyze a filing PDF."""

    def compare_filings(self, previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
        """Compare two filing PDFs."""


class PeerAgentProtocol(Protocol):
    """Protocol for a peer specialist agent."""

    def compare_peers(self, target_ticker: str, peer_tickers: Sequence[str] | None = None) -> PeerComparisonResponse:
        """Compare target ticker against peers."""


class ThesisAgentProtocol(Protocol):
    """Protocol for a thesis writer specialist agent."""

    def generate_report(self, thesis_input: ThesisInput) -> InvestmentReport:
        """Generate a final investment report from consolidated specialist outputs."""


class CoordinatorAgent:
    """Orchestrates specialist agents into a unified investment-research workflow."""

    def __init__(
        self,
        financial_agent: FinancialAgentProtocol | None = None,
        news_agent: NewsAgentProtocol | None = None,
        filings_agent: FilingsAgentProtocol | None = None,
        peer_agent: PeerAgentProtocol | None = None,
        thesis_agent: ThesisAgentProtocol | None = None,
    ) -> None:
        """Initialize with injectable specialist dependencies."""
        self._financial_agent = financial_agent or FinancialDataAgent()
        self._news_agent = news_agent or NewsAgent()
        self._filings_agent = filings_agent or FilingsAgent()
        self._peer_agent = peer_agent or PeerComparisonAgent()
        self._thesis_agent = thesis_agent or ThesisWriterAgent()

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
        """Run the complete specialist workflow and return a unified response."""
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

        if request.include_thesis:
            thesis_input = self._build_thesis_input(
                company_name=effective_company_name,
                financial_analysis=consolidated_data.financial_analysis,
                news_analysis=consolidated_data.news_analysis,
                filing_analysis=consolidated_data.filing_analysis,
                filing_comparison=consolidated_data.filing_comparison,
                peer_comparison=consolidated_data.peer_comparison,
            )
            consolidated_data.investment_report = self._execute_agent(
                "thesis_agent",
                lambda: self._thesis_agent.generate_report(thesis_input),
                metadata,
                completed_agents,
                failed_agents,
            )

        response = CoordinatorResponse(
            request=request,
            consolidated_data=consolidated_data,
            execution_metadata=metadata,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
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

    def _build_thesis_input(
        self,
        company_name: str,
        financial_analysis: FinancialAnalysis | None,
        news_analysis: NewsAgentResponse | None,
        filing_analysis: FilingAgentResponse | None,
        filing_comparison: FilingComparison | None,
        peer_comparison: PeerComparisonResponse | None,
    ) -> ThesisInput:
        """Convert specialist outputs into the thesis agent input model."""
        return ThesisInput(
            company_name=company_name,
            financial_analysis=self._render_financial_for_thesis(financial_analysis),
            news_analysis=self._render_news_for_thesis(news_analysis),
            filings_analysis=self._render_filings_for_thesis(filing_analysis, filing_comparison),
            peer_analysis=self._render_peers_for_thesis(peer_comparison),
        )

    def _render_financial_for_thesis(self, analysis: FinancialAnalysis | None) -> str:
        """Serialize financial analysis into a compact thesis context block."""
        if analysis is None:
            return "Financial analysis not available."
        metrics = analysis.metrics
        lines = [
            f"Ticker: {analysis.company.ticker}",
            f"Company: {analysis.company.name}",
            f"Sector: {analysis.company.sector or 'N/A'}",
            f"Industry: {analysis.company.industry or 'N/A'}",
            f"Market Cap: {metrics.market_cap}",
            f"Revenue: {metrics.revenue}",
            f"Net Income: {metrics.net_income}",
            f"PE Ratio: {metrics.pe_ratio}",
            f"EPS: {metrics.eps}",
            f"Operating Margin: {metrics.operating_margins}",
            f"ROE: {metrics.roe}",
            f"Revenue Growth: {metrics.revenue_growth}",
        ]
        if analysis.missing_fields:
            lines.append(f"Missing Fields: {', '.join(analysis.missing_fields)}")
        return "\n".join(lines)

    def _render_news_for_thesis(self, analysis: NewsAgentResponse | None) -> str | None:
        """Serialize news analysis into thesis context."""
        if analysis is None:
            return None
        summary = analysis.summary.summary if analysis.summary else ""
        events = "; ".join(analysis.summary.material_events) if analysis.summary else ""
        return (
            f"News window: {analysis.from_date} to {analysis.to_date}\n"
            f"Articles analyzed: {len(analysis.articles)}\n"
            f"Summary: {summary}\n"
            f"Material events: {events or 'None'}"
        )

    def _render_filings_for_thesis(
        self,
        filing_analysis: FilingAgentResponse | None,
        filing_comparison: FilingComparison | None,
    ) -> str | None:
        """Serialize filings analysis and comparison into thesis context."""
        if filing_analysis is None and filing_comparison is None:
            return None

        segments: list[str] = []
        if filing_analysis is not None:
            segments.append(f"Filing: {filing_analysis.filing_path}")
            segments.append(f"Summary: {filing_analysis.summary.summary}")
            if filing_analysis.summary.key_points:
                segments.append(f"Key points: {'; '.join(filing_analysis.summary.key_points)}")
            if filing_analysis.missing_sections:
                segments.append(f"Missing sections: {', '.join(filing_analysis.missing_sections)}")

        if filing_comparison is not None:
            segments.append(
                f"Comparison: {filing_comparison.previous_filing_path} -> {filing_comparison.current_filing_path}"
            )
            if filing_comparison.major_changes:
                segments.append(f"Major changes: {'; '.join(filing_comparison.major_changes)}")
            if filing_comparison.emerging_risks:
                segments.append(f"Emerging risks: {'; '.join(filing_comparison.emerging_risks)}")
            if filing_comparison.summary is not None:
                segments.append(f"Comparison summary: {filing_comparison.summary.summary}")

        return "\n".join(segments)

    def _render_peers_for_thesis(self, comparison: PeerComparisonResponse | None) -> str | None:
        """Serialize peer comparison into thesis context."""
        if comparison is None:
            return None
        lines = [
            f"Target: {comparison.target_ticker}",
            f"Peer set: {', '.join(comparison.peer_tickers)}",
            f"Available peers: {len(comparison.peers)}",
        ]
        if comparison.unavailable_tickers:
            lines.append(f"Unavailable peers: {', '.join(comparison.unavailable_tickers)}")
        return "\n".join(lines)


def generate_report(ticker: str) -> CoordinatorResponse:
    """Convenience function for running a coordinated research workflow."""
    return CoordinatorAgent().generate_report(ticker)
