"""Filings Agent for local annual and quarterly report analysis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from agents.filings_agent.models import (
    FilingAgentResponse,
    FilingComparison,
    FilingSection,
    FilingSummary,
)
from tools.filing_tools import FilingSummarizationError, FilingToolError, GeminiFilingSummarizer, PdfFilingTool

logger = logging.getLogger(__name__)


class FilingExtractionTool(Protocol):
    """Protocol for local filing extraction and comparison tools."""

    def analyze_filing(self, filing_path: str | Path) -> tuple[list[FilingSection], list[str]]:
        """Extract target sections from a filing."""

    def compare_filings(self, previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
        """Compare two filings and detect major changes."""


class FilingSummaryTool(Protocol):
    """Protocol for filing summarization tools."""

    def summarize(self, filing_path: Path, sections: list[FilingSection]) -> FilingSummary:
        """Summarize extracted filing sections."""

    def summarize_comparison(self, comparison: FilingComparison) -> FilingSummary:
        """Summarize a filing comparison."""


class FilingsAgent:
    """Agent responsible for filing analysis orchestration."""

    def __init__(
        self,
        filing_tool: FilingExtractionTool | None = None,
        summarizer: FilingSummaryTool | None = None,
    ) -> None:
        """Initialize the agent with injectable extraction and summary tools."""
        self._filing_tool = filing_tool or PdfFilingTool()
        self._summarizer = summarizer or GeminiFilingSummarizer()

    def analyze_filing(self, filing_path: str | Path) -> FilingAgentResponse:
        """Extract and summarize a local annual or quarterly PDF filing."""
        path = Path(filing_path)
        logger.info("FilingsAgent started filing analysis path=%s", path)
        try:
            sections, missing_sections = self._filing_tool.analyze_filing(path)
            summary = self._summarizer.summarize(path, sections)
        except (FilingToolError, FilingSummarizationError):
            logger.exception("FilingsAgent failed filing analysis path=%s", path)
            raise

        logger.info(
            "FilingsAgent completed filing analysis path=%s sections=%s missing_sections=%s",
            path,
            len(sections),
            missing_sections,
        )
        return FilingAgentResponse(
            filing_path=path,
            sections=sections,
            missing_sections=missing_sections,
            summary=summary,
        )

    def compare_filings(
        self,
        previous_filing_path: str | Path,
        current_filing_path: str | Path,
    ) -> FilingComparison:
        """Compare two local filing PDFs and summarize material changes."""
        logger.info(
            "FilingsAgent started filing comparison previous=%s current=%s",
            previous_filing_path,
            current_filing_path,
        )
        try:
            comparison = self._filing_tool.compare_filings(previous_filing_path, current_filing_path)
            comparison.summary = self._summarizer.summarize_comparison(comparison)
        except (FilingToolError, FilingSummarizationError):
            logger.exception(
                "FilingsAgent failed filing comparison previous=%s current=%s",
                previous_filing_path,
                current_filing_path,
            )
            raise

        logger.info(
            "FilingsAgent completed filing comparison changes=%s",
            len(comparison.major_changes),
        )
        return comparison


def analyze_filing(filing_path: str | Path) -> FilingAgentResponse:
    """Convenience function for analyzing a local filing PDF."""
    return FilingsAgent().analyze_filing(filing_path)


def compare_filings(previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
    """Convenience function for comparing two local filing PDFs."""
    return FilingsAgent().compare_filings(previous_filing_path, current_filing_path)
