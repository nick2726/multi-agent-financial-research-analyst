"""Pydantic models for coordinator orchestration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agents.filings_agent.models import (
    FilingAgentResponse,
    FilingComparison,
)
from agents.financial_agent.models import FinancialAnalysis
from agents.news_agent.models import NewsAgentResponse
from agents.peer_agent.models import PeerComparisonResponse
from agents.thesis_agent.models import InvestmentReport


class ResearchRequest(BaseModel):
    """Structured request accepted by the Coordinator Agent."""

    ticker: str = Field(..., min_length=1)
    company_name: Optional[str] = None
    filing_path: Optional[Path] = None
    previous_filing_path: Optional[Path] = None
    peer_tickers: Optional[list[str]] = None
    include_news: bool = True
    include_filings: bool = True
    include_peers: bool = True
    include_thesis: bool = True

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        """Normalize ticker symbols for downstream agents."""
        return value.strip().upper()

    @field_validator("company_name")
    @classmethod
    def normalize_company_name(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        """Strip optional company names."""
        if value is None:
            return None

        stripped_value = value.strip()

        return stripped_value or None


class AgentExecutionMetadata(BaseModel):
    """Execution status and timing for a specialist agent call."""

    agent_name: str
    status: str
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class ConsolidatedResearchData(BaseModel):
    """Aggregated specialist-agent outputs prepared for thesis generation."""

    financial_analysis: Optional[
        FinancialAnalysis
    ] = None

    news_analysis: Optional[
        NewsAgentResponse
    ] = None

    filing_analysis: Optional[
        FilingAgentResponse
    ] = None

    filing_comparison: Optional[
        FilingComparison
    ] = None

    peer_comparison: Optional[
        PeerComparisonResponse
    ] = None


class CoordinatorResponse(BaseModel):
    """Unified response returned by the Coordinator Agent."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
    )

    request: ResearchRequest

    consolidated_data: ConsolidatedResearchData

    execution_metadata: list[
        AgentExecutionMetadata
    ]

    completed_agents: list[str] = Field(
        default_factory=list
    )

    failed_agents: list[str] = Field(
        default_factory=list
    )

    investment_report: Optional[
        InvestmentReport
    ] = None

    @property
    def has_failures(self) -> bool:
        """Return whether any specialist agent failed."""
        return bool(self.failed_agents)

    @property
    def has_investment_report(self) -> bool:
        """Return whether thesis generation succeeded."""
        return self.investment_report is not None

    def to_thesis_input(self) -> dict[str, Any]:
        """Return a serializable payload for thesis generation."""
        return {
            "company_name": (
                self.request.company_name
                or self.request.ticker
            ),
            "financial_analysis": (
                self.consolidated_data.financial_analysis.model_dump(
                    mode="json"
                )
                if self.consolidated_data.financial_analysis
                else None
            ),
            "news_analysis": (
                self.consolidated_data.news_analysis.model_dump(
                    mode="json"
                )
                if self.consolidated_data.news_analysis
                else None
            ),
            "filing_analysis": (
                self.consolidated_data.filing_analysis.model_dump(
                    mode="json"
                )
                if self.consolidated_data.filing_analysis
                else None
            ),
            "filing_comparison": (
                self.consolidated_data.filing_comparison.model_dump(
                    mode="json"
                )
                if self.consolidated_data.filing_comparison
                else None
            ),
            "peer_comparison": (
                self.consolidated_data.peer_comparison.model_dump(
                    mode="json"
                )
                if self.consolidated_data.peer_comparison
                else None
            ),
        }