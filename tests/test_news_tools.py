"""Tests for NewsAPI and Gemini news tools."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import requests

from tools.news_tools import (
    EmptyNewsResponseError,
    GeminiNewsSummarizer,
    GeminiSummarizationError,
    InvalidCompanyNameError,
    NewsApiError,
    NewsApiRateLimitError,
    NewsApiTool,
)


class FakeResponse:
    """Minimal requests.Response stand-in."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        """Create a fake HTTP response."""
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        """Return the configured JSON payload."""
        return self._payload


class FakeSession:
    """HTTP session fake for NewsAPI tests."""

    def __init__(self, response: FakeResponse | None = None, raises: Exception | None = None) -> None:
        """Create a fake session with either a response or raised exception."""
        self.response = response
        self.raises = raises
        self.last_params: dict[str, Any] | None = None

    def get(self, endpoint: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        """Return the fake response while recording request params."""
        self.last_params = params
        if self.raises:
            raise self.raises
        if self.response is None:
            raise AssertionError("FakeSession requires a response when raises is not set.")
        return self.response


def _article(
    title: str,
    url: str,
    description: str = "TCS announced a major contract with a global bank.",
) -> dict[str, Any]:
    """Build a NewsAPI-style article fixture."""
    return {
        "title": title,
        "source": {"name": "Business Daily"},
        "publishedAt": "2026-06-01T10:00:00Z",
        "description": description,
        "url": url,
    }


def test_fetch_company_news_successful_retrieval_and_deduplication() -> None:
    """NewsApiTool should return filtered, deduplicated article models."""
    payload = {
        "status": "ok",
        "articles": [
            _article("TCS wins major contract", "https://example.com/tcs-contract"),
            _article("TCS wins major contract", "https://example.com/tcs-contract-duplicate"),
            _article(
                "Market opens flat",
                "https://example.com/market-open",
                description="Broad market update with no useful company information.",
            ),
            _article("TCS earnings announcement", "https://example.com/tcs-earnings"),
        ],
    }
    session = FakeSession(FakeResponse(status_code=200, payload=payload))

    articles = NewsApiTool(api_key="test-key", session=session).fetch_company_news(
        "TCS",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 6, 1),
        limit=20,
    )

    assert len(articles) == 2
    assert articles[0].title == "TCS wins major contract"
    assert articles[0].source == "Business Daily"
    assert str(articles[0].url) == "https://example.com/tcs-contract"
    assert session.last_params is not None
    assert session.last_params["q"] == "TCS"
    assert session.last_params["from"] == "2026-05-01"
    assert session.last_params["to"] == "2026-06-01"


def test_fetch_company_news_raises_for_empty_response() -> None:
    """NewsApiTool should raise when NewsAPI returns no articles."""
    session = FakeSession(FakeResponse(status_code=200, payload={"status": "ok", "articles": []}))

    with pytest.raises(EmptyNewsResponseError):
        NewsApiTool(api_key="test-key", session=session).fetch_company_news("INFY")


def test_fetch_company_news_rejects_invalid_company_name() -> None:
    """NewsApiTool should reject blank company names."""
    with pytest.raises(InvalidCompanyNameError):
        NewsApiTool(api_key="test-key").fetch_company_news(" ")


def test_fetch_company_news_wraps_request_failures() -> None:
    """NewsApiTool should convert network errors into NewsApiError."""
    session = FakeSession(raises=requests.Timeout("timeout"))

    with pytest.raises(NewsApiError):
        NewsApiTool(api_key="test-key", session=session).fetch_company_news("WIPRO")


def test_fetch_company_news_raises_rate_limit_error() -> None:
    """NewsApiTool should expose NewsAPI rate limits with a specific exception."""
    session = FakeSession(FakeResponse(status_code=429, payload={"status": "error"}))

    with pytest.raises(NewsApiRateLimitError):
        NewsApiTool(api_key="test-key", session=session).fetch_company_news("TCS")


def test_gemini_summarizer_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """GeminiNewsSummarizer should fail fast when GOOGLE_API_KEY is unavailable."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    summarizer = GeminiNewsSummarizer(api_key=None)

    with pytest.raises(GeminiSummarizationError):
        summarizer.summarize("TCS", [])


def test_gemini_summary_parser_handles_json_text() -> None:
    """GeminiNewsSummarizer should parse strict JSON model output."""
    summarizer = GeminiNewsSummarizer(api_key="test-key")

    summary = summarizer._parse_summary_text(
        '{"summary":"TCS won a major deal.","material_events":["Major contract"],'
        '"limitations":["Only two articles reviewed."]}'
    )

    assert summary.summary == "TCS won a major deal."
    assert summary.material_events == ["Major contract"]
    assert summary.limitations == ["Only two articles reviewed."]
