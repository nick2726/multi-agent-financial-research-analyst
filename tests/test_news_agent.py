"""Tests for the News Agent."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from agents.news_agent.models import NewsArticle, NewsSummary
from agents.news_agent.news_agent import NewsAgent
from tools.news_tools import GeminiSummarizationError


class FakeNewsTool:
    """News retrieval fake for testing agent orchestration."""

    def __init__(self, articles: list[NewsArticle]) -> None:
        """Create the fake tool with fixed articles."""
        self.articles = articles
        self.received_company_name: str | None = None
        self.received_from_date: date | None = None
        self.received_to_date: date | None = None
        self.received_limit: int | None = None

    def fetch_company_news(
        self,
        company_name: str,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Return fixed articles and record the request."""
        self.received_company_name = company_name
        self.received_from_date = from_date
        self.received_to_date = to_date
        self.received_limit = limit
        return self.articles


class FakeSummarizer:
    """Summarizer fake for testing News Agent behavior."""

    def __init__(self, summary: NewsSummary | None = None) -> None:
        """Create the fake summarizer with an optional fixed response."""
        self.summary = summary
        self.received_company_name: str | None = None
        self.received_articles: list[NewsArticle] | None = None

    def summarize(self, company_name: str, articles: list[NewsArticle]) -> NewsSummary:
        """Return a fixed summary or raise a Gemini-like failure."""
        self.received_company_name = company_name
        self.received_articles = articles
        if self.summary is None:
            raise GeminiSummarizationError("Gemini failed")
        return self.summary


def _news_article() -> NewsArticle:
    """Build a normalized article fixture."""
    return NewsArticle(
        title="INFY announces strategic partnership",
        source="Business Daily",
        publication_date=datetime.fromisoformat("2026-06-01T10:00:00+00:00"),
        description="Infosys announced a strategic partnership with a global enterprise.",
        url="https://example.com/infy-partnership",
    )


def test_news_agent_delegates_to_tool_and_summarizer() -> None:
    """NewsAgent should orchestrate retrieval and summarization without API calls."""
    article = _news_article()
    news_tool = FakeNewsTool([article])
    summarizer = FakeSummarizer(
        NewsSummary(
            summary="Infosys announced a strategic partnership.",
            material_events=["Strategic partnership"],
        )
    )

    response = NewsAgent(news_tool=news_tool, summarizer=summarizer).analyze_news(
        "INFY",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 6, 1),
        limit=10,
    )

    assert news_tool.received_company_name == "INFY"
    assert news_tool.received_from_date == date(2026, 5, 1)
    assert news_tool.received_to_date == date(2026, 6, 1)
    assert news_tool.received_limit == 10
    assert summarizer.received_company_name == "INFY"
    assert summarizer.received_articles == [article]
    assert response.company_name == "INFY"
    assert response.articles == [article]
    assert response.summary.material_events == ["Strategic partnership"]


def test_news_agent_uses_default_30_day_window() -> None:
    """NewsAgent should pass a default 30-day date range to the news tool."""
    article = _news_article()
    news_tool = FakeNewsTool([article])
    summarizer = FakeSummarizer(NewsSummary(summary="Summary"))

    response = NewsAgent(news_tool=news_tool, summarizer=summarizer).analyze_news("TCS")

    assert news_tool.received_from_date is not None
    assert news_tool.received_to_date is not None
    assert (news_tool.received_to_date - news_tool.received_from_date).days == 30
    assert response.company_name == "TCS"


def test_news_agent_propagates_gemini_failures() -> None:
    """NewsAgent should not hide summarization failures."""
    news_tool = FakeNewsTool([_news_article()])
    summarizer = FakeSummarizer(summary=None)

    with pytest.raises(GeminiSummarizationError):
        NewsAgent(news_tool=news_tool, summarizer=summarizer).analyze_news("WIPRO")
