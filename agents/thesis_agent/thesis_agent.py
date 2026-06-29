"""Thesis Writer Agent with Gemini-first generation and deterministic fallback."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from agents.thesis_agent.gemini_service import GeminiService
from agents.thesis_agent.models import InvestmentReport, ThesisInput
from agents.thesis_agent.prompts import THESIS_TEMPLATE

logger = logging.getLogger(__name__)

REPORT_HEADERS = [
    "Executive Summary",
    "Bull Case",
    "Bear Case",
    "Key Risks",
    "Peer Positioning",
    "Investment Thesis",
    "Conclusion",
]


class ThesisWriterAgent:
    """Generate a structured investment thesis from specialist agent outputs.

    Gemini remains the preferred path. For local demos and offline judging, the
    agent falls back to a deterministic, grounded report built only from the
    supplied specialist context.
    """

    def __init__(self, gemini_service: GeminiService | None = None, allow_fallback: bool = True) -> None:
        self._gemini = gemini_service
        self._allow_fallback = allow_fallback

    def generate_report(self, thesis_input: ThesisInput) -> InvestmentReport:
        """Generate a balanced investment report."""
        logger.info("Generating thesis report for %s", thesis_input.company_name)
        prompt = THESIS_TEMPLATE.format(
            company_name=thesis_input.company_name,
            financial_analysis=thesis_input.financial_analysis,
            news_analysis=thesis_input.news_analysis or "Not available.",
            filings_analysis=thesis_input.filings_analysis or "Not available.",
            peer_analysis=thesis_input.peer_analysis or "Not available.",
        )

        try:
            gemini = self._gemini or GeminiService()
            response = gemini.generate(prompt)
            print("\n" + "=" * 80)
            print("RAW GEMINI RESPONSE")
            print("=" * 80)
            print(response)
            print("=" * 80 + "\n")
            report = self._parse_report(response)
            report.source = "gemini"
            return report
        except Exception as exc:
            if not self._allow_fallback:
                logger.exception("Failed generating thesis report.")
                raise RuntimeError("Thesis report generation failed.") from exc
            logger.warning(
                "Gemini thesis generation unavailable; using deterministic fallback: %s",
                exc,
            )
            return self._build_fallback_report(thesis_input)

    def _parse_report(self, report_text: str) -> InvestmentReport:
        sections = {}

        normalized = report_text.replace("**", "")

        for index, header in enumerate(REPORT_HEADERS):

            pattern = re.compile(
                rf"(?:^|\n)\s*(?:#+\s*)?{re.escape(header)}\s*:?\s*",
                re.IGNORECASE,
            )

            match = pattern.search(normalized)

            if match is None:
                sections[header] = "Section not generated."
                continue

            end = len(normalized)

            for next_header in REPORT_HEADERS[index + 1:]:

                next_pattern = re.compile(
                    rf"(?:^|\n)\s*(?:#+\s*)?{re.escape(next_header)}\s*:?\s*",
                    re.IGNORECASE,
                )

                next_match = next_pattern.search(normalized, match.end())

                if next_match:
                    end = next_match.start()
                    break

            sections[header] = (
                normalized[match.end():end].strip()
                or "Section not generated."
            )

        return InvestmentReport(
            executive_summary=sections["Executive Summary"],
            bull_case=sections["Bull Case"],
            bear_case=sections["Bear Case"],
            key_risks=sections["Key Risks"],
            peer_positioning=sections["Peer Positioning"],
            investment_thesis=sections["Investment Thesis"],
            conclusion=sections["Conclusion"],
        )

    def _build_fallback_report(self, thesis_input: ThesisInput) -> InvestmentReport:
        """Build a useful report without external LLM calls."""
        facts = _ContextFacts.from_input(thesis_input)
        positive_points = facts.positive_points()
        caution_points = facts.caution_points()
        risk_points = facts.risk_points()

        return InvestmentReport(
            executive_summary=(
                f"{thesis_input.company_name} was analyzed using the available financial, news, "
                "filings, and peer-comparison context. "
                f"The strongest observable positives are {self._join_points(positive_points[:2])}. "
                f"The main cautions are {self._join_points(caution_points[:2])}."
            ),
            bull_case=self._bullet_block(positive_points),
            bear_case=self._bullet_block(caution_points),
            key_risks=self._bullet_block(risk_points),
            peer_positioning=facts.peer_positioning(),
            investment_thesis=(
                "A constructive view is justified only if the company sustains growth, margins, and "
                "execution quality relative to peers. A neutral or cautious stance is more appropriate "
                "if valuation is demanding, key data is missing, or recent filings/news point to rising "
                "operational or regulatory risk."
            ),
            conclusion=(
                "Overall, the thesis should be treated as research support rather than a buy/sell call. "
                "The next diligence step is to validate the agent output against the latest exchange "
                "filings, management commentary, and analyst consensus before making an investment decision."
            ),
            source="deterministic_fallback",
        )

    def _bullet_block(self, points: Iterable[str]) -> str:
        selected = [point for point in points if point]
        if not selected:
            return "- No material evidence was available in the supplied context."
        return "\n".join(f"- {point}" for point in selected[:5])

    def _join_points(self, points: list[str]) -> str:
        if not points:
            return "limited based on supplied data"
        if len(points) == 1:
            return points[0]
        return f"{points[0]} and {points[1]}"


class _ContextFacts:
    """Small parser for deterministic thesis generation."""

    def __init__(self, thesis_input: ThesisInput) -> None:
        self.company_name = thesis_input.company_name
        self.financial = thesis_input.financial_analysis or ""
        self.news = thesis_input.news_analysis or ""
        self.filings = thesis_input.filings_analysis or ""
        self.peers = thesis_input.peer_analysis or ""
        self.combined = "\n".join([self.financial, self.news, self.filings, self.peers])

    @classmethod
    def from_input(cls, thesis_input: ThesisInput) -> "_ContextFacts":
        return cls(thesis_input)

    def positive_points(self) -> list[str]:
        points = []
        growth = self._metric("Revenue Growth")
        margin = self._metric("Operating Margin")
        roe = self._metric("ROE")
        if growth and not growth.strip().startswith("-"):
            points.append(f"Revenue growth is positive at {growth}.")
        if margin:
            points.append(f"Operating profitability is visible with operating margin of {margin}.")
        if roe:
            points.append(f"Return on equity is reported at {roe}, indicating shareholder-return efficiency.")
        points.extend(self._extract_prefixed("Material events", self.news, limit=2))
        points.extend(self._extract_prefixed("Key points", self.filings, limit=2))
        if not points:
            points.append("Core company and market data were retrieved, giving the team a factual base for discussion.")
        return points

    def caution_points(self) -> list[str]:
        points = []
        pe_ratio = self._metric("PE Ratio")
        missing = self._extract_prefixed("Missing Fields", self.financial, limit=1)
        if pe_ratio:
            points.append(f"Valuation needs scrutiny because the reported P/E ratio is {pe_ratio}.")
        if missing:
            points.append(f"Data quality is incomplete: {missing[0]}.")
        if "Not available" in self.combined:
            points.append("Some specialist context was unavailable, so the thesis should be updated as more evidence arrives.")
        points.extend(self._extract_prefixed("Emerging risks", self.filings, limit=2))
        if not points:
            points.append("No clear bear-case trigger was found in the supplied context, but valuation and execution risks remain relevant.")
        return points

    def risk_points(self) -> list[str]:
        points = self._extract_prefixed("Emerging risks", self.filings, limit=3)
        points.extend(self._extract_prefixed("Missing sections", self.filings, limit=1))
        points.extend(self._extract_prefixed("Limitations", self.news, limit=2))
        if not points:
            points = [
                "Market-data and news APIs can be incomplete or delayed.",
                "The model uses supplied evidence only and does not replace analyst verification.",
                "Macroeconomic, currency, regulatory, and sector-cycle risks may affect the outcome.",
            ]
        return points

    def peer_positioning(self) -> str:
        target = self._extract_line("Target", self.peers)
        peer_set = self._extract_line("Peer set", self.peers)
        available = self._extract_line("Available peers", self.peers)
        if target or peer_set or available:
            return "\n".join(
                item for item in [
                    f"Target: {target}" if target else "",
                    f"Peer universe: {peer_set}" if peer_set else "",
                    f"Comparable companies with data: {available}" if available else "",
                    "Relative valuation should be interpreted with sector, scale, and profitability differences in mind.",
                ]
                if item
            )
        return "Peer comparison was unavailable or insufficient for a relative valuation view."

    def _metric(self, name: str) -> str | None:
        value = self._extract_line(name, self.financial)
        if value in {None, "None", "N/A"}:
            return None
        return value

    def _extract_line(self, label: str, text: str) -> str | None:
        match = re.search(rf"^{re.escape(label)}\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_prefixed(self, label: str, text: str, limit: int) -> list[str]:
        value = self._extract_line(label, text)
        if not value or value.lower() in {"none", "n/a"}:
            return []
        parts = [part.strip(" -") for part in re.split(r";|,\s(?=[A-Z])", value) if part.strip(" -")]
        return parts[:limit]
