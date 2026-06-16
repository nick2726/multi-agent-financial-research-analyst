"""Financial Data Agent.

The agent coordinates financial-data retrieval but delegates all yfinance access
to tools. This keeps orchestration separate from external data source concerns.
"""

from __future__ import annotations

import logging
from typing import Protocol

from agents.financial_agent.models import FinancialAnalysis
from tools.financial_tools import FinancialDataError, FinancialDataTool

logger = logging.getLogger(__name__)


class FinancialAnalysisTool(Protocol):
    """Protocol for a tool that can return financial analysis for a ticker."""

    def get_financial_analysis(self, ticker: str) -> FinancialAnalysis:
        """Return structured financial analysis for a ticker."""


class FinancialDataAgent:
    """Agent responsible for financial-data analysis orchestration."""

    def __init__(self, financial_tool: FinancialAnalysisTool | None = None) -> None:
        """Initialize the agent with an injectable financial data tool."""
        self._financial_tool = financial_tool or FinancialDataTool()

    def analyze_company(self, ticker: str) -> FinancialAnalysis:
        """Analyze a company by delegating retrieval to the financial data tool.

        Args:
            ticker: Exchange ticker symbol accepted by the configured tool.

        Raises:
            FinancialDataError: When the financial tool cannot return analysis.
        """
        logger.info("FinancialDataAgent started analysis for ticker=%s", ticker)
        try:
            analysis = self._financial_tool.get_financial_analysis(ticker)
        except FinancialDataError:
            logger.exception("FinancialDataAgent failed for ticker=%s", ticker)
            raise

        logger.info(
            "FinancialDataAgent completed analysis for ticker=%s missing_fields=%s",
            analysis.company.ticker,
            analysis.missing_fields,
        )
        return analysis
