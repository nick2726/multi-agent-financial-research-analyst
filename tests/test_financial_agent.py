"""Tests for the Financial Data Agent."""

from __future__ import annotations

import pytest

from agents.financial_agent.financial_agent import FinancialDataAgent
from agents.financial_agent.models import CompanyInfo, FinancialAnalysis, FinancialMetrics
from tools.financial_tools import FinancialDataSourceError


class FakeFinancialTool:
    """Tool fake for testing agent orchestration without yfinance."""

    def __init__(self, response: FinancialAnalysis | None = None) -> None:
        """Create a fake tool with an optional fixed response."""
        self.response = response
        self.received_ticker: str | None = None

    def get_financial_analysis(self, ticker: str) -> FinancialAnalysis:
        """Return a fixed response and record the requested ticker."""
        self.received_ticker = ticker
        if self.response is None:
            raise FinancialDataSourceError("tool failed")
        return self.response


def test_financial_agent_delegates_to_tool() -> None:
    """FinancialDataAgent should delegate analysis to the injected tool."""
    response = FinancialAnalysis(
        company=CompanyInfo(ticker="TCS.NS", name="Tata Consultancy Services Limited"),
        metrics=FinancialMetrics(market_cap=12_000_000_000),
        missing_fields=["revenue"],
    )
    tool = FakeFinancialTool(response=response)

    analysis = FinancialDataAgent(financial_tool=tool).analyze_company("tcs.ns")

    assert tool.received_ticker == "tcs.ns"
    assert analysis.company.ticker == "TCS.NS"
    assert analysis.metrics.market_cap == 12_000_000_000
    assert analysis.missing_fields == ["revenue"]


def test_financial_agent_propagates_tool_failures() -> None:
    """FinancialDataAgent should not hide tool-level failures."""
    agent = FinancialDataAgent(financial_tool=FakeFinancialTool())

    with pytest.raises(FinancialDataSourceError):
        agent.analyze_company("TCS.NS")
