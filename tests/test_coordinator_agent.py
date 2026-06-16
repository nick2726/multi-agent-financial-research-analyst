"""Tests for the Coordinator Agent."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from agents.coordinator.coordinator_agent import CoordinatorAgent
from agents.filings_agent.models import FilingAgentResponse, FilingComparison, FilingSection, FilingSummary
from agents.financial_agent.models import CompanyInfo, FinancialAnalysis, FinancialMetrics
from agents.news_agent.models import NewsAgentResponse, NewsArticle, NewsSummary
from agents.peer_agent.models import PeerComparisonResponse, PeerComparisonTable, PeerMetrics
from agents.thesis_agent.models import InvestmentReport, ThesisInput


class FakeFinancialAgent:
    """Financial agent fake for coordinator tests."""

    def __init__(self, should_fail: bool = False) -> None:
        """Create the fake financial agent."""
        self.should_fail = should_fail

    def analyze_company(self, ticker: str) -> FinancialAnalysis:
        """Return a fixed financial analysis or raise."""
        if self.should_fail:
            raise RuntimeError("financial failed")
        return FinancialAnalysis(
            company=CompanyInfo(ticker=ticker, name="Infosys Limited"),
            metrics=FinancialMetrics(market_cap=10_000, pe_ratio=25),
        )


class FakeNewsAgent:
    """News agent fake for coordinator tests."""

    def __init__(self, should_fail: bool = False) -> None:
        """Create the fake news agent."""
        self.should_fail = should_fail
        self.received_company_name: str | None = None

    def analyze_news(self, company_name: str) -> NewsAgentResponse:
        """Return fixed news analysis or raise."""
        self.received_company_name = company_name
        if self.should_fail:
            raise RuntimeError("news failed")
        return NewsAgentResponse(
            company_name=company_name,
            query=company_name,
            from_date=date(2026, 5, 1),
            to_date=date(2026, 6, 1),
            articles=[
                NewsArticle(
                    title="Infosys wins strategic contract",
                    source="Business Daily",
                    publication_date=datetime.fromisoformat("2026-06-01T10:00:00+00:00"),
                    description="Infosys won a strategic contract.",
                    url="https://example.com/infosys-contract",
                )
            ],
            summary=NewsSummary(summary="Infosys won a strategic contract."),
        )


class FakeFilingsAgent:
    """Filings agent fake for coordinator tests."""

    def analyze_filing(self, filing_path: str | Path) -> FilingAgentResponse:
        """Return fixed filing analysis."""
        return FilingAgentResponse(
            filing_path=Path(filing_path),
            sections=[
                FilingSection(
                    name="Business Overview",
                    content="Infosys provides digital services.",
                    start_character=0,
                    end_character=40,
                )
            ],
            summary=FilingSummary(summary="Filing summary."),
        )

    def compare_filings(self, previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
        """Return fixed filing comparison."""
        return FilingComparison(
            previous_filing_path=Path(previous_filing_path),
            current_filing_path=Path(current_filing_path),
            major_changes=["Revenue growth/decline: Revenue grew."],
        )


class FakePeerAgent:
    """Peer agent fake for coordinator tests."""

    def __init__(self, should_fail: bool = False) -> None:
        """Create the fake peer agent."""
        self.should_fail = should_fail

    def compare_peers(self, target_ticker: str, peer_tickers: list[str] | None = None) -> PeerComparisonResponse:
        """Return fixed peer comparison or raise."""
        if self.should_fail:
            raise RuntimeError("peer failed")
        peers = [
            PeerMetrics(
                ticker=target_ticker,
                company_name="Infosys Limited",
                market_cap=10_000,
                pe_ratio=25,
            )
        ]
        return PeerComparisonResponse(
            target_ticker=target_ticker,
            peer_tickers=peer_tickers or ["TCS.NS"],
            peers=peers,
            rankings=[],
            comparison_table=PeerComparisonTable(
                columns=["ticker", "company_name"],
                rows=[{"ticker": target_ticker, "company_name": "Infosys Limited"}],
            ),
        )


class FakeThesisAgent:
    """Thesis agent fake for coordinator tests."""

    def __init__(self, should_fail: bool = False) -> None:
        """Create the fake thesis agent."""
        self.should_fail = should_fail

    def generate_report(self, thesis_input: ThesisInput) -> InvestmentReport:
        """Return a fixed investment report or raise."""
        if self.should_fail:
            raise RuntimeError("thesis failed")
        return InvestmentReport(
            executive_summary="Fake Executive Summary",
            bull_case="Fake Bull Case",
            bear_case="Fake Bear Case",
            key_risks="Fake Key Risks",
            peer_positioning="Fake Peer Positioning",
            investment_thesis="Fake Investment Thesis",
            conclusion="Fake Conclusion",
        )


def _coordinator(
    financial_agent: FakeFinancialAgent | None = None,
    news_agent: FakeNewsAgent | None = None,
    peer_agent: FakePeerAgent | None = None,
    thesis_agent: FakeThesisAgent | None = None,
) -> CoordinatorAgent:
    """Build a coordinator with fake specialist agents."""
    return CoordinatorAgent(
        financial_agent=financial_agent or FakeFinancialAgent(),
        news_agent=news_agent or FakeNewsAgent(),
        filings_agent=FakeFilingsAgent(),
        peer_agent=peer_agent or FakePeerAgent(),
        thesis_agent=thesis_agent or FakeThesisAgent(),
    )


def test_coordinator_successful_orchestration() -> None:
    """CoordinatorAgent should run specialists and aggregate their outputs."""
    response = _coordinator().generate_report(
        "infy.ns",
        filing_path="data/filings/INFY_2025.pdf",
        previous_filing_path="data/filings/INFY_2024.pdf",
        peer_tickers=["TCS.NS"],
    )

    assert response.request.ticker == "INFY.NS"
    assert response.consolidated_data.financial_analysis is not None
    assert response.consolidated_data.news_analysis is not None
    assert response.consolidated_data.filing_analysis is not None
    assert response.consolidated_data.filing_comparison is not None
    assert response.consolidated_data.peer_comparison is not None
    assert response.investment_report is not None
    assert response.failed_agents == []
    assert set(response.completed_agents) == {
        "financial_agent",
        "news_agent",
        "filings_agent",
        "filings_comparison",
        "peer_agent",
        "thesis_agent",
    }


def test_coordinator_continues_after_partial_agent_failures() -> None:
    """CoordinatorAgent should preserve successful outputs when one agent fails."""
    response = _coordinator(news_agent=FakeNewsAgent(should_fail=True)).generate_report("INFY.NS", include_thesis=False)

    assert response.consolidated_data.financial_analysis is not None
    assert response.consolidated_data.news_analysis is None
    assert response.consolidated_data.peer_comparison is not None
    assert response.failed_agents == ["news_agent"]
    failed_metadata = next(item for item in response.execution_metadata if item.agent_name == "news_agent")
    assert failed_metadata.status == "failed"
    assert failed_metadata.error_type == "RuntimeError"
    assert failed_metadata.error_message == "news failed"


def test_coordinator_derives_company_name_from_financial_output() -> None:
    """CoordinatorAgent should use financial company name for news when available."""
    news_agent = FakeNewsAgent()

    _coordinator(news_agent=news_agent).generate_report("INFY.NS")

    assert news_agent.received_company_name == "Infosys Limited"


def test_coordinator_uses_ticker_for_news_when_financial_agent_fails() -> None:
    """CoordinatorAgent should continue using ticker as fallback company query."""
    news_agent = FakeNewsAgent()

    response = _coordinator(
        financial_agent=FakeFinancialAgent(should_fail=True),
        news_agent=news_agent,
    ).generate_report("INFY.NS")

    assert news_agent.received_company_name == "INFY.NS"
    assert "financial_agent" in response.failed_agents
    assert response.consolidated_data.news_analysis is not None


def test_coordinator_can_skip_optional_agents() -> None:
    """CoordinatorAgent should honor include flags for optional specialists."""
    response = _coordinator().generate_report(
        "INFY.NS",
        include_news=False,
        include_filings=False,
        include_peers=False,
        include_thesis=False,
    )

    assert response.consolidated_data.financial_analysis is not None
    assert response.consolidated_data.news_analysis is None
    assert response.consolidated_data.filing_analysis is None
    assert response.consolidated_data.peer_comparison is None
    assert response.completed_agents == ["financial_agent"]


def test_coordinator_thesis_agent_failure() -> None:
    """CoordinatorAgent should handle thesis agent failures gracefully."""
    response = _coordinator(thesis_agent=FakeThesisAgent(should_fail=True)).generate_report("INFY.NS")

    assert response.consolidated_data.financial_analysis is not None
    assert response.investment_report is None
    assert "thesis_agent" in response.failed_agents
