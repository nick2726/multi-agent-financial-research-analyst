"""Tools for extracting, analyzing, and summarizing filing PDFs.

The Filings Agent uses this module instead of opening PDFs or calling Gemini
directly. Automated NSE/BSE/SEC retrieval can later be added behind this layer.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Optional, Protocol

import pdfplumber
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from agents.filings_agent.models import FilingComparison, FilingSection, FilingSummary

logger = logging.getLogger(__name__)

SECTION_PATTERNS: Mapping[str, tuple[str, ...]] = {
    "Management Discussion and Analysis": (
        r"management\s+discussion\s+and\s+analysis",
        r"management\s+discussion\s*&\s*analysis",
        r"\bmd\s*&\s*a\b",
    ),
    "Risk Factors": (
        r"risk\s+factors",
        r"principal\s+risks",
        r"enterprise\s+risk\s+management",
    ),
    "Business Overview": (
        r"business\s+overview",
        r"company\s+overview",
        r"our\s+business",
    ),
    "Financial Highlights": (
        r"financial\s+highlights",
        r"performance\s+highlights",
        r"key\s+financial\s+highlights",
    ),
    "Corporate Governance Highlights": (
        r"corporate\s+governance",
        r"governance\s+highlights",
    ),
}

CHANGE_PATTERNS: Mapping[str, tuple[str, ...]] = {
    "Revenue growth/decline": (
        r"revenue\s+(?:grew|increased|declined|decreased|growth|drop)",
        r"sales\s+(?:grew|increased|declined|decreased)",
    ),
    "Margin expansion/contraction": (
        r"margin\s+(?:expanded|contracted|improved|declined)",
        r"operating\s+margin",
        r"ebit\s+margin",
    ),
    "New strategic initiatives": (
        r"strategic\s+initiative",
        r"new\s+initiative",
        r"transformation\s+program",
    ),
    "Management guidance changes": (
        r"guidance\s+(?:revised|raised|lowered|changed)",
        r"outlook\s+(?:improved|weakened|revised)",
    ),
    "Emerging risks": (
        r"emerging\s+risk",
        r"new\s+risk",
        r"risk\s+has\s+increased",
    ),
    "Significant investments or acquisitions": (
        r"acquisition",
        r"investment",
        r"capex",
        r"capital\s+expenditure",
    ),
}


class FilingToolError(Exception):
    """Base exception for filing analysis failures."""


class MissingFilingFileError(FilingToolError):
    """Raised when a filing PDF path does not exist."""


class CorruptedFilingPdfError(FilingToolError):
    """Raised when a filing PDF cannot be opened or parsed."""


class EmptyFilingDocumentError(FilingToolError):
    """Raised when a filing PDF has no extractable text."""


class MissingFilingSectionError(FilingToolError):
    """Raised when none of the requested sections are found."""


class FilingSummarizationError(FilingToolError):
    """Raised when Gemini cannot summarize a filing."""


class FilingSummarizer(Protocol):
    """Protocol for filing summarization components."""

    def summarize(self, filing_path: Path, sections: Sequence[FilingSection]) -> FilingSummary:
        """Summarize filing sections."""

    def summarize_comparison(self, comparison: FilingComparison) -> FilingSummary:
        """Summarize major year-over-year filing changes."""


class PdfFilingTool:
    """Extract text and structured sections from local filing PDFs."""

    def extract_text(self, filing_path: str | Path) -> str:
        """Extract normalized raw text from a local PDF filing.

        Args:
            filing_path: Path to a manually supplied PDF report.

        Raises:
            MissingFilingFileError: If the path does not exist.
            CorruptedFilingPdfError: If pdfplumber cannot parse the PDF.
            EmptyFilingDocumentError: If no text can be extracted.
        """
        path = self._validate_pdf_path(filing_path)
        logger.info("Extracting filing text path=%s", path)
        try:
            with pdfplumber.open(path) as pdf:
                page_text = [page.extract_text() or "" for page in pdf.pages]
        except FilingToolError:
            raise
        except Exception as exc:
            logger.exception("Failed to parse filing PDF path=%s", path)
            raise CorruptedFilingPdfError(f"Unable to parse PDF filing '{path}'.") from exc

        normalized_text = self.normalize_text("\n".join(page_text))
        if not normalized_text:
            logger.warning("Filing PDF contains no extractable text path=%s", path)
            raise EmptyFilingDocumentError(f"PDF filing '{path}' contains no extractable text.")
        return normalized_text

    def extract_sections(self, text: str) -> tuple[list[FilingSection], list[str]]:
        """Extract target filing sections using pattern matching."""
        normalized_text = self.normalize_text(text)
        if not normalized_text:
            raise EmptyFilingDocumentError("Filing text is empty.")

        matches = self._find_section_matches(normalized_text)
        sections: list[FilingSection] = []
        missing_sections: list[str] = []
        ordered_matches = sorted(matches, key=lambda item: item[1])

        for index, (section_name, start_position) in enumerate(ordered_matches):
            next_start = (
                ordered_matches[index + 1][1]
                if index + 1 < len(ordered_matches)
                else len(normalized_text)
            )
            content = normalized_text[start_position:next_start].strip()
            if content:
                sections.append(
                    FilingSection(
                        name=section_name,
                        content=content,
                        start_character=start_position,
                        end_character=next_start,
                    )
                )

        found_names = {section.name for section in sections}
        for section_name in SECTION_PATTERNS:
            if section_name not in found_names:
                missing_sections.append(section_name)

        if not sections:
            logger.warning("No target filing sections found")
            raise MissingFilingSectionError("No target filing sections were found.")

        logger.info("Extracted filing sections count=%s missing=%s", len(sections), missing_sections)
        return sections, missing_sections

    def analyze_filing(self, filing_path: str | Path) -> tuple[list[FilingSection], list[str]]:
        """Extract raw text and target sections from a local PDF filing."""
        text = self.extract_text(filing_path)
        return self.extract_sections(text)

    def compare_filings(self, previous_filing_path: str | Path, current_filing_path: str | Path) -> FilingComparison:
        """Compare two filing PDFs and detect major year-over-year changes."""
        previous_path = self._validate_pdf_path(previous_filing_path)
        current_path = self._validate_pdf_path(current_filing_path)
        previous_text = self.extract_text(previous_path)
        current_text = self.extract_text(current_path)

        major_changes = self._detect_major_changes(previous_text, current_text)
        emerging_risks = self._extract_matching_sentences(current_text, CHANGE_PATTERNS["Emerging risks"])
        strategic_initiatives = self._extract_matching_sentences(
            current_text,
            CHANGE_PATTERNS["New strategic initiatives"],
        )
        return FilingComparison(
            previous_filing_path=previous_path,
            current_filing_path=current_path,
            major_changes=major_changes,
            emerging_risks=emerging_risks,
            strategic_initiatives=strategic_initiatives,
        )

    def normalize_text(self, text: str) -> str:
        """Normalize filing text while preserving sentence boundaries."""
        text = BeautifulSoup(text, "html.parser").get_text(" ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _validate_pdf_path(self, filing_path: str | Path) -> Path:
        """Validate that a local filing path exists and points to a PDF file."""
        path = Path(filing_path)
        if not path.exists():
            logger.warning("Filing path does not exist path=%s", path)
            raise MissingFilingFileError(f"Filing PDF '{path}' does not exist.")
        if path.suffix.lower() != ".pdf":
            raise MissingFilingFileError(f"Filing path '{path}' must be a PDF file.")
        return path

    def _find_section_matches(self, text: str) -> list[tuple[str, int]]:
        """Find the first occurrence of each target section in normalized text."""
        matches: list[tuple[str, int]] = []
        for section_name, patterns in SECTION_PATTERNS.items():
            positions = [
                match.start()
                for pattern in patterns
                for match in re.finditer(pattern, text, flags=re.IGNORECASE)
            ]
            if positions:
                matches.append((section_name, min(positions)))
        return matches

    def _detect_major_changes(self, previous_text: str, current_text: str) -> list[str]:
        """Detect material YoY changes mentioned in the current filing."""
        changes: list[str] = []
        previous_lower = previous_text.lower()
        for change_name, patterns in CHANGE_PATTERNS.items():
            current_sentences = self._extract_matching_sentences(current_text, patterns)
            new_sentences = [
                sentence for sentence in current_sentences if sentence.lower() not in previous_lower
            ]
            if new_sentences:
                changes.append(f"{change_name}: {new_sentences[0]}")
        return changes

    def _extract_matching_sentences(self, text: str, patterns: Sequence[str]) -> list[str]:
        """Extract sentences that match any provided regex pattern."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        matches: list[str] = []
        for sentence in sentences:
            if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in patterns):
                matches.append(sentence.strip())
        return matches[:5]


class ExtractiveFilingSummarizer:
    """Local filing summarizer used when Gemini is unavailable."""

    def summarize(self, filing_path: Path, sections: Sequence[FilingSection]) -> FilingSummary:
        """Summarize extracted filing sections without external model calls."""
        if not sections:
            raise FilingSummarizationError("At least one filing section is required.")
        key_points = []
        for section in sections[:5]:
            sentence = self._first_material_sentence(section.content)
            key_points.append(f"{section.name}: {sentence}")
        return FilingSummary(
            summary=f"Extracted {len(sections)} material sections from {filing_path.name} for analyst review.",
            key_points=key_points,
            limitations=["Generated with local extractive summarization; review the original filing before investment use."],
        )

    def summarize_comparison(self, comparison: FilingComparison) -> FilingSummary:
        """Summarize detected year-over-year filing changes locally."""
        key_points = [*comparison.major_changes[:3], *comparison.emerging_risks[:2], *comparison.strategic_initiatives[:2]]
        if not key_points:
            key_points = ["No major text-pattern changes were detected in the configured sections."]
        return FilingSummary(
            summary="Year-over-year filing comparison completed using deterministic pattern matching.",
            key_points=key_points,
            limitations=["Change detection is pattern-based and should be validated against the full filing."],
        )

    def _first_material_sentence(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for sentence in sentences:
            cleaned = sentence.strip()
            if len(cleaned.split()) >= 8:
                return cleaned[:350]
        return text.strip()[:350]

class GeminiFilingSummarizer:
    """Summarize filing sections and comparisons using Gemini."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash") -> None:
        """Initialize the summarizer with Gemini configuration."""
        load_dotenv()
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name

    def summarize(self, filing_path: Path, sections: Sequence[FilingSection]) -> FilingSummary:
        """Generate a concise filing summary from extracted sections."""
        if not self._api_key:
            logger.warning("GOOGLE_API_KEY is missing for filing summarization")
            raise FilingSummarizationError("GOOGLE_API_KEY must be set in .env.")
        if not sections:
            raise FilingSummarizationError("At least one filing section is required.")
        prompt = self._build_filing_prompt(filing_path, sections)
        return self._generate_summary(prompt)

    def summarize_comparison(self, comparison: FilingComparison) -> FilingSummary:
        """Generate a concise comparison summary from detected major changes."""
        if not self._api_key:
            logger.warning("GOOGLE_API_KEY is missing for filing comparison summarization")
            raise FilingSummarizationError("GOOGLE_API_KEY must be set in .env.")
        prompt = (
            "You are a financial research analyst. Summarize these year-over-year filing "
            "changes as strict JSON with keys summary, key_points, and limitations. "
            "key_points and limitations must be arrays of strings.\n\n"
            f"Previous filing: {comparison.previous_filing_path}\n"
            f"Current filing: {comparison.current_filing_path}\n"
            f"Major changes: {comparison.major_changes}\n"
            f"Emerging risks: {comparison.emerging_risks}\n"
            f"Strategic initiatives: {comparison.strategic_initiatives}"
        )
        return self._generate_summary(prompt)

    def _build_filing_prompt(self, filing_path: Path, sections: Sequence[FilingSection]) -> str:
        """Build a compact Gemini prompt from extracted filing sections."""
        section_blocks = []
        for section in sections:
            section_blocks.append(
                f"Section: {section.name}\nContent:\n{section.content[:3500]}"
            )
        return (
            "You are a financial research analyst. Summarize this filing for investment "
            "research. Focus on MD&A, risks, business overview, financial highlights, "
            "corporate governance, revenue or margin changes, strategic initiatives, "
            "management guidance, investments, and acquisitions. Return strict JSON with "
            "keys summary, key_points, and limitations. key_points and limitations must be "
            f"arrays of strings.\n\nFiling path: {filing_path}\n\n"
            + "\n\n".join(section_blocks)
        )

    def _generate_summary(self, prompt: str) -> FilingSummary:
        """Call Gemini and parse a FilingSummary response."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model_name)
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
        except Exception as exc:
            logger.exception("Gemini filing summarization failed")
            raise FilingSummarizationError("Gemini failed to summarize filing data.") from exc

        if not text or not text.strip():
            raise FilingSummarizationError("Gemini returned an empty filing summary.")
        return self._parse_summary_text(text)

    def _parse_summary_text(self, text: str) -> FilingSummary:
        """Parse Gemini JSON output, falling back to plain text when needed."""
        cleaned_text = text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
            cleaned_text = cleaned_text.removeprefix("json").strip()
        try:
            payload = json.loads(cleaned_text)
        except json.JSONDecodeError:
            return FilingSummary(
                summary=cleaned_text,
                key_points=[],
                limitations=["Gemini returned non-JSON text; parsed as plain summary."],
            )
        return FilingSummary(
            summary=str(payload.get("summary", "")).strip(),
            key_points=[str(item) for item in payload.get("key_points", [])],
            limitations=[str(item) for item in payload.get("limitations", [])],
        )


def analyze_filing(filing_path: str | Path) -> tuple[list[FilingSection], list[str]]:
    """Convenience function for extracting sections from a local PDF filing."""
    return PdfFilingTool().analyze_filing(filing_path)

