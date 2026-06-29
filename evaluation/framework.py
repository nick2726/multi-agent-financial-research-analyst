"""Evaluation framework for generated investment research responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationResult:
    """Aggregated evaluation scores."""

    completeness_score: float
    reliability_score: float
    thesis_quality_score: float
    overall_score: float
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "completeness_score": self.completeness_score,
            "reliability_score": self.reliability_score,
            "thesis_quality_score": self.thesis_quality_score,
            "overall_score": self.overall_score,
            "notes": self.notes,
        }


class ResearchEvaluationFramework:
    """Rule-based evaluation framework for milestone scoring."""

    def evaluate_response(self, response_payload: dict[str, Any]) -> EvaluationResult:
        notes: list[str] = []

        consolidated = response_payload.get("consolidated_data") or {}
        completed_agents = response_payload.get("completed_agents") or []
        failed_agents = response_payload.get("failed_agents") or []

        expected_sections = [
            "financial_analysis",
            "news_analysis",
            "filing_analysis",
            "peer_comparison",
            "investment_report",
        ]
        present_sections = sum(1 for section in expected_sections if consolidated.get(section) is not None)
        completeness_score = round((present_sections / len(expected_sections)) * 100, 2)

        total_agents = len(completed_agents) + len(failed_agents)
        if total_agents == 0:
            reliability_score = 0.0
            notes.append("No agent execution metadata was found.")
        else:
            reliability_score = round((len(completed_agents) / total_agents) * 100, 2)

        thesis_report = consolidated.get("investment_report") or {}
        thesis_sections = [
            "executive_summary",
            "bull_case",
            "bear_case",
            "key_risks",
            "peer_positioning",
            "investment_thesis",
            "conclusion",
        ]
        non_empty_thesis_sections = 0
        for section in thesis_sections:
            content = (thesis_report.get(section) or "").strip()
            if content and "Section not generated" not in content:
                non_empty_thesis_sections += 1
        thesis_quality_score = round((non_empty_thesis_sections / len(thesis_sections)) * 100, 2)

        if failed_agents:
            notes.append(f"Failed specialist agents: {', '.join(failed_agents)}")
        if thesis_quality_score < 100:
            notes.append("Thesis report is partially generated.")

        overall_score = round((0.4 * completeness_score) + (0.3 * reliability_score) + (0.3 * thesis_quality_score), 2)
        notes.append(f"Completed agents: {len(completed_agents)}")
        notes.append(f"Failed agents: {len(failed_agents)}")
        return EvaluationResult(
            completeness_score=completeness_score,
            reliability_score=reliability_score,
            thesis_quality_score=thesis_quality_score,
            overall_score=overall_score,
            notes=notes,
        )
