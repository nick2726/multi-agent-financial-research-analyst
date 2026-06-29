"""Tests for peer comparison tools."""

from __future__ import annotations

import pytest

from agents.financial_agent.models import CompanyInfo, FinancialAnalysis, FinancialMetrics
from tools.financial_tools import FinancialDataSourceError
from tools.peer_tools import InvalidPeerInputError, NoPeerDataError, PeerComparisonTool


class FakeFinancialDataProvider:
    """Financial data provider fake for peer tool tests."""

    def __init__(self, analyses: dict[str, FinancialAnalysis]) -> None:
        """Create the provider with ticker-keyed financial analyses."""
        self.analyses = analyses
        self.received_tickers: list[str] = []

    def get_financial_analysis(self, ticker: str) -> FinancialAnalysis:
        """Return a configured analysis or simulate unavailable data."""
        normalized_ticker = ticker.upper()
        self.received_tickers.append(normalized_ticker)
        if normalized_ticker not in self.analyses:
            raise FinancialDataSourceError(f"No data for {ticker}")
        return self.analyses[normalized_ticker]


def _analysis(
    ticker: str,
    market_cap: float | None,
    pe_ratio: float | None,
    revenue_growth: float | None,
    operating_margins: float | None,
    roe: float | None,
    eps: float | None,
) -> FinancialAnalysis:
    """Build a financial analysis fixture."""
    return FinancialAnalysis(
        company=CompanyInfo(ticker=ticker, name=f"{ticker} Limited"),
        metrics=FinancialMetrics(
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            revenue_growth=revenue_growth,
            operating_margins=operating_margins,
            roe=roe,
            eps=eps,
        ),
    )


def test_compare_peers_successful_comparison() -> None:
    """PeerComparisonTool should compare explicit peers and rank metrics."""
    provider = FakeFinancialDataProvider(
        {
            "INFY.NS": _analysis("INFY.NS", 10_000, 25, 0.12, 0.24, 0.30, 60),
            "TCS.NS": _analysis("TCS.NS", 15_000, 30, 0.10, 0.26, 0.35, 80),
            "WIPRO.NS": _analysis("WIPRO.NS", 5_000, 18, 0.06, 0.18, 0.20, 35),
        }
    )

    response = PeerComparisonTool(provider).compare_peers(
        "infy.ns",
        peer_tickers=["tcs.ns", "wipro.ns"],
    )

    assert response.target_ticker == "INFY.NS"
    assert response.peer_tickers == ["TCS.NS", "WIPRO.NS"]
    assert len(response.peers) == 3
    assert response.comparison_table.columns == [
        "ticker",
        "company_name",
        "market_cap",
        "pe_ratio",
        "revenue_growth",
        "operating_margin",
        "roe",
        "eps",
    ]
    pe_rankings = [rank for rank in response.rankings if rank.metric == "pe_ratio"]
    assert pe_rankings[0].ticker == "WIPRO.NS"
    growth_rankings = [rank for rank in response.rankings if rank.metric == "revenue_growth"]
    assert growth_rankings[0].ticker == "INFY.NS"


def test_compare_peers_tracks_missing_data_and_unavailable_tickers() -> None:
    """PeerComparisonTool should keep partial rows and record unavailable peers."""
    provider = FakeFinancialDataProvider(
        {
            "INFY.NS": _analysis("INFY.NS", 10_000, None, 0.12, None, 0.30, 60),
            "TCS.NS": _analysis("TCS.NS", 15_000, 30, 0.10, 0.26, 0.35, 80),
        }
    )

    response = PeerComparisonTool(provider).compare_peers(
        "INFY.NS",
        peer_tickers=["TCS.NS", "MISSING.NS"],
    )

    target = next(peer for peer in response.peers if peer.ticker == "INFY.NS")
    assert "pe_ratio" in target.missing_fields
    assert "operating_margin" in target.missing_fields
    assert response.unavailable_tickers == ["MISSING.NS"]


def test_compare_peers_rejects_invalid_target() -> None:
    """PeerComparisonTool should reject blank target tickers."""
    with pytest.raises(InvalidPeerInputError):
        PeerComparisonTool(FakeFinancialDataProvider({})).compare_peers(" ")


def test_identify_peers_supports_default_indian_it_universe() -> None:
    """PeerComparisonTool should provide curated Indian IT peers by default."""
    peers = PeerComparisonTool(FakeFinancialDataProvider({})).identify_peers("INFY.NS")

    assert "TCS.NS" in peers
    assert "WIPRO.NS" in peers
    assert "LTIMINDTREE.NS" in peers
    assert "INFY.NS" not in peers


def test_compare_peers_raises_when_no_data_available() -> None:
    """PeerComparisonTool should fail if target and peers are all unavailable."""
    provider = FakeFinancialDataProvider({})

    with pytest.raises(NoPeerDataError):
        PeerComparisonTool(provider).compare_peers("INFY.NS", peer_tickers=["TCS.NS"])
