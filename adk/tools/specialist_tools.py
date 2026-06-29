"""ADK tool wrappers for existing specialist agents.

These wrappers keep the original agent implementations untouched and expose
stable callable interfaces for ADK-style orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

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


class FinancialAgentTool:
    """ADK wrapper for financial analysis."""

    def __init__(self, agent: FinancialDataAgent | None = None) -> None:
        self._agent = agent or FinancialDataAgent()

    def run(self, ticker: str) -> FinancialAnalysis:
        return self._agent.analyze_company(ticker)


class NewsAgentTool:
    """ADK wrapper for news analysis."""

    def __init__(self, agent: NewsAgent | None = None) -> None:
        self._agent = agent or NewsAgent()

    def run(self, company_name: str) -> NewsAgentResponse:
        return self._agent.analyze_news(company_name)


class FilingsAgentTool:
    """ADK wrapper for filings analysis and comparison."""

    def __init__(self, agent: FilingsAgent | None = None) -> None:
        self._agent = agent or FilingsAgent()

    def analyze(self, filing_path: str | Path) -> FilingAgentResponse:
        return self._agent.analyze_filing(filing_path)

    def compare(self, previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
        return self._agent.compare_filings(previous_filing_path, current_filing_path)


class PeerAgentTool:
    """ADK wrapper for peer comparison."""

    def __init__(self, agent: PeerComparisonAgent | None = None) -> None:
        self._agent = agent or PeerComparisonAgent()

    def run(self, target_ticker: str, peer_tickers: Sequence[str] | None = None) -> PeerComparisonResponse:
        return self._agent.compare_peers(target_ticker, peer_tickers)


class ThesisAgentTool:
    """ADK wrapper for thesis report generation."""

    def __init__(self, agent: ThesisWriterAgent | None = None) -> None:
        self._agent = agent or ThesisWriterAgent()

    def run(self, thesis_input: ThesisInput) -> InvestmentReport:
        return self._agent.generate_report(thesis_input)
