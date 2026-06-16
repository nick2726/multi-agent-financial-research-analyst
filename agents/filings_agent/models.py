"""Pydantic models for filing analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FilingSection(BaseModel):
    """Extracted section from an annual or quarterly filing."""

    name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    start_character: int = Field(..., ge=0)
    end_character: int = Field(..., ge=0)
    found: bool = True


class FilingSummary(BaseModel):
    """Gemini-generated filing summary."""

    summary: str
    key_points: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class FilingComparison(BaseModel):
    """Structured comparison between two filings."""

    previous_filing_path: Path
    current_filing_path: Path
    major_changes: list[str] = Field(default_factory=list)
    emerging_risks: list[str] = Field(default_factory=list)
    strategic_initiatives: list[str] = Field(default_factory=list)
    summary: Optional[FilingSummary] = None


class FilingAgentResponse(BaseModel):
    """Structured response produced by the Filings Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    filing_path: Path
    document_type: str = "manual_pdf"
    sections: list[FilingSection]
    missing_sections: list[str] = Field(default_factory=list)
    summary: FilingSummary
    comparison: Optional[FilingComparison] = None
    source: str = "local_pdf"
