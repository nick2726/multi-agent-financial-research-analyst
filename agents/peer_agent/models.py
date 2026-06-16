"""Pydantic models for peer comparison analysis."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PeerMetrics(BaseModel):
    """Comparable valuation and performance metrics for one peer company."""

    ticker: str = Field(..., min_length=1)
    company_name: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    eps: Optional[float] = None
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        """Normalize ticker symbols for stable comparisons."""
        return value.strip().upper()


class PeerRank(BaseModel):
    """Rank assigned to a peer for a specific metric."""

    ticker: str
    metric: str
    rank: int
    value: Optional[float] = None


class PeerComparisonTable(BaseModel):
    """Tabular peer comparison output."""

    columns: list[str]
    rows: list[dict[str, object]]


class PeerComparisonResponse(BaseModel):
    """Structured response produced by the Peer Comparison Agent."""

    model_config = ConfigDict(extra="forbid")

    target_ticker: str
    peer_tickers: list[str]
    peers: list[PeerMetrics]
    rankings: list[PeerRank]
    comparison_table: PeerComparisonTable
    unavailable_tickers: list[str] = Field(default_factory=list)
    source: str = "yfinance"
