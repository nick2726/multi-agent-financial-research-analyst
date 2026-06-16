"""Tests for yfinance-backed financial tools."""

from __future__ import annotations

import pandas as pd
import pytest

from tools.financial_tools import (
    FinancialDataSourceError,
    FinancialDataTool,
    InvalidTickerError,
    MissingFinancialDataError,
)


class FakeTicker:
    """Minimal yfinance.Ticker stand-in for unit tests."""

    def __init__(
        self,
        info: dict,
        financials: pd.DataFrame | None = None,
        balance_sheet: pd.DataFrame | None = None,
    ) -> None:
        """Create a fake ticker with yfinance-like attributes."""
        self.info = info
        self.financials = financials if financials is not None else pd.DataFrame()
        self.balance_sheet = balance_sheet if balance_sheet is not None else pd.DataFrame()


class BrokenTicker:
    """Ticker that simulates an upstream data source failure."""

    @property
    def info(self) -> dict:
        """Raise a network-like failure when company info is requested."""
        raise TimeoutError("network timeout")


def test_get_financial_analysis_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """FinancialDataTool should return normalized metrics for a valid ticker."""
    financials = pd.DataFrame(
        {
            "2025": [1000.0, 100.0],
            "2024": [800.0, 80.0],
        },
        index=["Total Revenue", "Net Income"],
    )
    balance_sheet = pd.DataFrame(
        {"2025": [500.0]},
        index=["Stockholders Equity"],
    )
    fake_ticker = FakeTicker(
        info={
            "longName": "Tata Consultancy Services Limited",
            "quoteType": "EQUITY",
            "sector": "Technology",
            "industry": "Information Technology Services",
            "country": "India",
            "currency": "INR",
            "exchange": "NSI",
            "trailingEps": 120.5,
            "trailingPE": 28.2,
            "marketCap": 12_000_000_000,
            "operatingMargins": 0.25,
        },
        financials=financials,
        balance_sheet=balance_sheet,
    )
    monkeypatch.setattr("tools.financial_tools.yf.Ticker", lambda ticker: fake_ticker)

    analysis = FinancialDataTool().get_financial_analysis("tcs.ns")

    assert analysis.company.ticker == "TCS.NS"
    assert analysis.company.name == "Tata Consultancy Services Limited"
    assert analysis.metrics.revenue == 1000.0
    assert analysis.metrics.net_income == 100.0
    assert analysis.metrics.eps == 120.5
    assert analysis.metrics.pe_ratio == 28.2
    assert analysis.metrics.market_cap == 12_000_000_000
    assert analysis.metrics.revenue_growth == 0.25
    assert analysis.metrics.operating_margins == 0.25
    assert analysis.metrics.roe == 0.2
    assert analysis.missing_fields == []


def test_get_financial_analysis_rejects_blank_ticker() -> None:
    """FinancialDataTool should reject empty ticker input before calling yfinance."""
    with pytest.raises(InvalidTickerError):
        FinancialDataTool().get_financial_analysis(" ")


def test_get_financial_analysis_rejects_unknown_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    """FinancialDataTool should raise InvalidTickerError for empty yfinance info."""
    monkeypatch.setattr(
        "tools.financial_tools.yf.Ticker",
        lambda ticker: FakeTicker(info={}),
    )

    with pytest.raises(InvalidTickerError):
        FinancialDataTool().get_financial_analysis("INVALID")


def test_get_financial_analysis_tracks_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """FinancialDataTool should expose partially missing metrics without hiding them."""
    fake_ticker = FakeTicker(
        info={
            "shortName": "Example Ltd",
            "quoteType": "EQUITY",
            "marketCap": 1000,
        }
    )
    monkeypatch.setattr("tools.financial_tools.yf.Ticker", lambda ticker: fake_ticker)

    analysis = FinancialDataTool().get_financial_analysis("EXAMPLE")

    assert analysis.metrics.market_cap == 1000.0
    assert "revenue" in analysis.missing_fields
    assert "net_income" in analysis.missing_fields
    assert "eps" in analysis.missing_fields


def test_get_financial_analysis_raises_when_all_metrics_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FinancialDataTool should fail when no useful metrics are available."""
    fake_ticker = FakeTicker(
        info={
            "shortName": "No Metrics Ltd",
            "quoteType": "EQUITY",
        }
    )
    monkeypatch.setattr("tools.financial_tools.yf.Ticker", lambda ticker: fake_ticker)

    with pytest.raises(MissingFinancialDataError):
        FinancialDataTool().get_financial_analysis("NOMETRICS")


def test_get_financial_analysis_wraps_data_source_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FinancialDataTool should convert upstream failures into domain exceptions."""
    monkeypatch.setattr("tools.financial_tools.yf.Ticker", lambda ticker: BrokenTicker())

    with pytest.raises(FinancialDataSourceError):
        FinancialDataTool().get_financial_analysis("TCS.NS")
