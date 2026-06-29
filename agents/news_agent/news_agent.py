"""News Agent for company news analysis."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from agents.news_agent.models import NewsAgentResponse, NewsArticle, NewsSummary
from tools.news_tools import ExtractiveNewsSummarizer, GeminiNewsSummarizer, NewsApiTool, NewsToolError

logger = logging.getLogger(__name__)


class CompanyNewsTool(Protocol):
    """Protocol for retrieving normalized company news articles."""

    def fetch_company_news(
        self,
        company_name: str,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Fetch company news articles."""


class CompanyNewsSummarizer(Protocol):
    """Protocol for summarizing company news articles."""

    def summarize(self, company_name: str, articles: list[NewsArticle]) -> NewsSummary:
        """Summarize company news articles."""


class NewsAgent:
    """Agent responsible for company news retrieval and summarization."""

    def __init__(
        self,
        news_tool: CompanyNewsTool | None = None,
        summarizer: CompanyNewsSummarizer | None = None,
        fallback_summarizer: CompanyNewsSummarizer | None = None,
    ) -> None:
        """Initialize the agent with injectable tool and summarizer dependencies."""
        self._news_tool = news_tool or NewsApiTool()
        self._summarizer = summarizer or GeminiNewsSummarizer()
        self._fallback_summarizer = fallback_summarizer or ExtractiveNewsSummarizer()

    def analyze_news(
        self,
        company_name: str,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 20,
    ) -> NewsAgentResponse:
        """Retrieve and summarize recent company news."""
        normalized_to_date = to_date or datetime.now(UTC).date()
        normalized_from_date = from_date or normalized_to_date - timedelta(days=30)
        logger.info(
            "NewsAgent started company=%s from_date=%s to_date=%s limit=%s",
            company_name,
            normalized_from_date,
            normalized_to_date,
            limit,
        )

        try:
            articles = self._news_tool.fetch_company_news(
                company_name=company_name,
                from_date=normalized_from_date,
                to_date=normalized_to_date,
                limit=limit,
            )
        except NewsToolError:
            logger.exception("NewsAgent failed during retrieval company=%s", company_name)
            raise

        try:
            summary = self._summarizer.summarize(company_name, articles)
        except NewsToolError as exc:
            logger.warning("Primary news summarizer unavailable; using local fallback: %s", exc)
            summary = self._fallback_summarizer.summarize(company_name, articles)

        logger.info(
            "NewsAgent completed company=%s article_count=%s material_event_count=%s",
            company_name,
            len(articles),
            len(summary.material_events),
        )
        return NewsAgentResponse(
            company_name=company_name.strip(),
            query=company_name.strip(),
            from_date=normalized_from_date,
            to_date=normalized_to_date,
            articles=articles,
            summary=summary,
        )


def analyze_news(company_name: str) -> NewsAgentResponse:
    """Convenience function for analyzing recent company news."""
    return NewsAgent().analyze_news(company_name)
