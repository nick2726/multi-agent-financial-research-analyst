"""Tests for filing extraction and summarization tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agents.filings_agent.models import FilingSection
from tools.filing_tools import (
    CorruptedFilingPdfError,
    EmptyFilingDocumentError,
    FilingSummarizationError,
    GeminiFilingSummarizer,
    MissingFilingFileError,
    MissingFilingSectionError,
    PdfFilingTool,
)


class FakePage:
    """Minimal pdfplumber page stand-in."""

    def __init__(self, text: str | None) -> None:
        """Create a fake PDF page."""
        self._text = text

    def extract_text(self) -> str | None:
        """Return configured page text."""
        return self._text


class FakePdf:
    """Context manager stand-in for pdfplumber PDF objects."""

    def __init__(self, pages: list[FakePage]) -> None:
        """Create a fake PDF with pages."""
        self.pages = pages

    def __enter__(self) -> "FakePdf":
        """Enter the fake PDF context."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the fake PDF context."""


def _create_pdf_path(tmp_path: Path, name: str = "INFY_2025.pdf") -> Path:
    """Create a placeholder PDF path for validation tests."""
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4 placeholder")
    return path


def _filing_text() -> str:
    """Return filing text containing all target sections."""
    return (
        "Business Overview Infosys provides digital services. "
        "Financial Highlights Revenue grew by 12 percent and operating margin expanded. "
        "Management Discussion and Analysis The company launched a strategic initiative. "
        "Risk Factors Emerging risk from AI regulation has increased. "
        "Corporate Governance Highlights The board strengthened governance oversight."
    )


def test_extract_text_and_sections_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PdfFilingTool should extract normalized text and target sections from PDFs."""
    pdf_path = _create_pdf_path(tmp_path)
    monkeypatch.setattr(
        "tools.filing_tools.pdfplumber.open",
        lambda path: FakePdf([FakePage(_filing_text())]),
    )

    sections, missing_sections = PdfFilingTool().analyze_filing(pdf_path)

    assert len(sections) == 5
    assert missing_sections == []
    assert sections[0].name == "Business Overview"
    assert "Infosys provides digital services" in sections[0].content


def test_extract_sections_reports_missing_sections() -> None:
    """PdfFilingTool should return section names that were not found."""
    text = "Business Overview The company operates globally. Risk Factors Competition is intense."

    sections, missing_sections = PdfFilingTool().extract_sections(text)

    assert [section.name for section in sections] == ["Business Overview", "Risk Factors"]
    assert "Financial Highlights" in missing_sections
    assert "Management Discussion and Analysis" in missing_sections


def test_extract_text_rejects_invalid_file_path(tmp_path: Path) -> None:
    """PdfFilingTool should raise when the PDF path is missing."""
    with pytest.raises(MissingFilingFileError):
        PdfFilingTool().extract_text(tmp_path / "missing.pdf")


def test_extract_text_wraps_corrupted_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PdfFilingTool should convert parser failures into CorruptedFilingPdfError."""
    pdf_path = _create_pdf_path(tmp_path)

    def raise_corrupted_pdf(path: Path) -> None:
        raise ValueError("bad pdf")

    monkeypatch.setattr("tools.filing_tools.pdfplumber.open", raise_corrupted_pdf)

    with pytest.raises(CorruptedFilingPdfError):
        PdfFilingTool().extract_text(pdf_path)


def test_extract_text_rejects_empty_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PdfFilingTool should raise when no text can be extracted."""
    pdf_path = _create_pdf_path(tmp_path)
    monkeypatch.setattr(
        "tools.filing_tools.pdfplumber.open",
        lambda path: FakePdf([FakePage(None), FakePage("   ")]),
    )

    with pytest.raises(EmptyFilingDocumentError):
        PdfFilingTool().extract_text(pdf_path)


def test_extract_sections_raises_when_no_target_sections() -> None:
    """PdfFilingTool should raise when no required section headings are found."""
    with pytest.raises(MissingFilingSectionError):
        PdfFilingTool().extract_sections("This document has unrelated content only.")


def test_compare_filings_detects_major_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PdfFilingTool should detect major YoY changes in current filings."""
    previous_pdf = _create_pdf_path(tmp_path, "INFY_2024.pdf")
    current_pdf = _create_pdf_path(tmp_path, "INFY_2025.pdf")
    texts = {
        previous_pdf: "Financial Highlights Revenue was stable. Risk Factors Competition remains intense.",
        current_pdf: (
            "Financial Highlights Revenue grew by 12 percent. "
            "Management Discussion and Analysis A new strategic initiative was launched. "
            "Risk Factors Emerging risk from regulation has increased. "
            "The company announced an acquisition."
        ),
    }
    monkeypatch.setattr(
        PdfFilingTool,
        "extract_text",
        lambda self, path: texts[Path(path)],
    )

    comparison = PdfFilingTool().compare_filings(previous_pdf, current_pdf)

    assert any("Revenue growth/decline" in change for change in comparison.major_changes)
    assert any("New strategic initiatives" in change for change in comparison.major_changes)
    assert comparison.emerging_risks
    assert comparison.strategic_initiatives


def test_gemini_filing_summarizer_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """GeminiFilingSummarizer should fail fast without GOOGLE_API_KEY."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr("tools.filing_tools.load_dotenv", lambda *args, **kwargs: None)
    summarizer = GeminiFilingSummarizer(api_key=None)
    sections = [
        FilingSection(
            name="Business Overview",
            content="The company provides technology services.",
            start_character=0,
            end_character=41,
        )
    ]

    with pytest.raises(FilingSummarizationError):
        summarizer.summarize(Path("data/filings/INFY_2025.pdf"), sections)


def test_gemini_filing_summary_parser_handles_json_text() -> None:
    """GeminiFilingSummarizer should parse strict JSON output."""
    summary = GeminiFilingSummarizer(api_key="test-key")._parse_summary_text(
        '{"summary":"Revenue grew.","key_points":["Revenue growth"],'
        '"limitations":["Only extracted sections reviewed."]}'
    )

    assert summary.summary == "Revenue grew."
    assert summary.key_points == ["Revenue growth"]
    assert summary.limitations == ["Only extracted sections reviewed."]
