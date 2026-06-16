import logging
from typing import Dict

from agents.thesis_agent.gemini_service import GeminiService
from agents.thesis_agent.models import (
    InvestmentReport,
    ThesisInput,
)
from agents.thesis_agent.prompts import (
    THESIS_TEMPLATE,
)

logger = logging.getLogger(__name__)


class ThesisWriterAgent:

    def __init__(
        self,
        gemini_service: GeminiService | None = None,
    ):

        self._gemini = (
            gemini_service
            if gemini_service
            else GeminiService()
        )

    def generate_report(
        self,
        thesis_input: ThesisInput,
    ) -> InvestmentReport:

        logger.info(
            "Generating thesis report for %s",
            thesis_input.company_name,
        )

        prompt = THESIS_TEMPLATE.format(
            company_name=thesis_input.company_name,
            financial_analysis=thesis_input.financial_analysis,
            news_analysis=(
                thesis_input.news_analysis
                or "Not available."
            ),
            filings_analysis=(
                thesis_input.filings_analysis
                or "Not available."
            ),
            peer_analysis=(
                thesis_input.peer_analysis
                or "Not available."
            ),
        )

        try:

            response = self._gemini.generate(
                prompt
            )

            return self._parse_report(
                response
            )

        except Exception as exc:

            logger.exception(
                "Failed generating thesis report."
            )

            raise RuntimeError(
                "Thesis report generation failed."
            ) from exc

    def _parse_report(
        self,
        report_text: str,
    ) -> InvestmentReport:

        sections = {}

        headers = [
            "Executive Summary",
            "Bull Case",
            "Bear Case",
            "Key Risks",
            "Peer Positioning",
            "Investment Thesis",
            "Conclusion",
        ]

        for i, header in enumerate(
            headers
        ):

            start = report_text.find(
                header
            )

            if start == -1:

                sections[
                    header
                ] = (
                    "Section not generated."
                )

                continue

            end = len(report_text)

            for next_header in headers[
                i + 1 :
            ]:

                next_pos = (
                    report_text.find(
                        next_header,
                        start + 1,
                    )
                )

                if next_pos != -1:

                    end = next_pos

                    break

            content = report_text[
                start
                + len(header) :
                end
            ].strip(
                ": \n"
            )

            sections[
                header
            ] = content

        return InvestmentReport(
            executive_summary=sections[
                "Executive Summary"
            ],
            bull_case=sections[
                "Bull Case"
            ],
            bear_case=sections[
                "Bear Case"
            ],
            key_risks=sections[
                "Key Risks"
            ],
            peer_positioning=sections[
                "Peer Positioning"
            ],
            investment_thesis=sections[
                "Investment Thesis"
            ],
            conclusion=sections[
                "Conclusion"
            ],
        )