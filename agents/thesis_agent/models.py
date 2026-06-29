"""Pydantic models for thesis generation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ThesisInput(BaseModel):
    """Consolidated specialist context passed to the Thesis Writer Agent."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    financial_analysis: str
    news_analysis: Optional[str] = None
    filings_analysis: Optional[str] = None
    peer_analysis: Optional[str] = None


class InvestmentReport(BaseModel):
    """Structured investment report returned by the Thesis Writer Agent."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    bull_case: str
    bear_case: str
    key_risks: str
    peer_positioning: str
    investment_thesis: str
    conclusion: str
    source: str = Field(
        default="gemini",
        description="Report generation path: gemini or deterministic_fallback.",
    )
