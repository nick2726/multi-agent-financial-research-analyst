"""Pydantic models for financial analysis outputs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyInfo(BaseModel):
    """Basic company metadata returned by the financial data tool."""

    ticker: str = Field(..., min_length=1)
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        """Normalize ticker symbols to uppercase for consistent downstream use."""
        return value.strip().upper()


class FinancialMetrics(BaseModel):
    """Key financial metrics used by the Financial Data Agent."""

    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    revenue_growth: Optional[float] = None
    operating_margins: Optional[float] = None
    roe: Optional[float] = None


class FinancialAnalysis(BaseModel):
    """Structured response produced by the Financial Data Agent."""

    model_config = ConfigDict(extra="forbid")

    company: CompanyInfo
    metrics: FinancialMetrics
    missing_fields: list[str] = Field(default_factory=list)
    source: str = "yfinance"
