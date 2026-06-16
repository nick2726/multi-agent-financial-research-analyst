"""Tests for the Filings Agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.filings_agent.filings_agent import FilingsAgent
from agents.filings_agent.models import FilingComparison, FilingSection, FilingSummary
from tools.filing_tools import FilingSummarizationError


class FakeFilingTool:
    """Filing extraction fake for testing agent orchestration."""

    def __init__(self, sections: list[FilingSection]) -> None:
        """Create the fake filing tool."""
        self.sections = sections
        self.received_filing_path: Path | None = None

    def analyze_filing(self, filing_path: str | Path) -> tuple[list[FilingSection], list[str]]:
        """Return fixed sections and record the request."""
        self.received_filing_path = Path(filing_path)
        return self.sections, ["Risk Factors"]

    def compare_filings(self, previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
        """Return a fixed comparison."""
        return FilingComparison(
            previous_filing_path=Path(previous_filing_path),
            current_filing_path=Path(current_filing_path),
            major_changes=["Revenue growth/decline: Revenue grew by 12 percent."],
        )


class FakeFilingSummarizer:
    """Filing summarizer fake for agent tests."""

    def __init__(self, summary: FilingSummary | None = None) -> None:
        """Create a fake summarizer with optional fixed response."""
        self.summary = summary
        self.received_sections: list[FilingSection] | None = None

    def summarize(self, filing_path: Path, sections: list[FilingSection]) -> FilingSummary:
        """Return a fixed summary or raise a Gemini-like failure."""
        self.received_sections = sections
        if self.summary is None:
            raise FilingSummarizationError("Gemini failed")
        return self.summary

    def summarize_comparison(self, comparison: FilingComparison) -> FilingSummary:
        """Return a fixed comparison summary or raise a Gemini-like failure."""
        if self.summary is None:
            raise FilingSummarizationError("Gemini failed")
        return self.summary


def _section() -> FilingSection:
    """Build a filing section fixture."""
    return FilingSection(
        name="Business Overview",
        content="The company provides digital services.",
        start_character=0,
        end_character=38,
    )


def test_filings_agent_delegates_analysis_to_tools() -> None:
    """FilingsAgent should orchestrate extraction and summarization only."""
    section = _section()
    filing_tool = FakeFilingTool([section])
    summarizer = FakeFilingSummarizer(
        FilingSummary(summary="The company provides digital services.", key_points=["Business overview"])
    )

    response = FilingsAgent(filing_tool=filing_tool, summarizer=summarizer).analyze_filing(
        "data/filings/INFY_2025.pdf"
    )

    assert filing_tool.received_filing_path == Path("data/filings/INFY_2025.pdf")
    assert summarizer.received_sections == [section]
    assert response.filing_path == Path("data/filings/INFY_2025.pdf")
    assert response.sections == [section]
    assert response.missing_sections == ["Risk Factors"]
    assert response.summary.key_points == ["Business overview"]


def test_filings_agent_delegates_comparison_to_tools() -> None:
    """FilingsAgent should summarize comparison results from the filing tool."""
    agent = FilingsAgent(
        filing_tool=FakeFilingTool([_section()]),
        summarizer=FakeFilingSummarizer(FilingSummary(summary="Revenue improved.")),
    )

    comparison = agent.compare_filings(
        "data/filings/INFY_2024.pdf",
        "data/filings/INFY_2025.pdf",
    )

    assert comparison.previous_filing_path == Path("data/filings/INFY_2024.pdf")
    assert comparison.current_filing_path == Path("data/filings/INFY_2025.pdf")
    assert comparison.major_changes
    assert comparison.summary is not None
    assert comparison.summary.summary == "Revenue improved."


def test_filings_agent_propagates_gemini_failures() -> None:
    """FilingsAgent should not hide summarization failures."""
    agent = FilingsAgent(
        filing_tool=FakeFilingTool([_section()]),
        summarizer=FakeFilingSummarizer(summary=None),
    )

    with pytest.raises(FilingSummarizationError):
        agent.analyze_filing("data/filings/INFY_2025.pdf")
