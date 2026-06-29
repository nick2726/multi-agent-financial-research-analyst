"""Tools for retrieving and summarizing company news.

The News Agent depends on this module instead of calling NewsAPI or Gemini
directly. That boundary makes external services mockable and replaceable.
"""

from __future__ import annotations

import json
import logging
import os
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Optional, Protocol
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

from agents.news_agent.models import NewsArticle, NewsSummary

logger = logging.getLogger(__name__)

NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"
GOOGLE_NEWS_RSS_ENDPOINT = "https://news.google.com/rss/search"
MATERIAL_EVENT_KEYWORDS = (
    "acquisition",
    "acquires",
    "merger",
    "contract",
    "deal",
    "partnership",
    "earnings",
    "results",
    "revenue",
    "profit",
    "ceo",
    "cfo",
    "leadership",
    "regulatory",
    "lawsuit",
    "litigation",
    "settlement",
    "guidance",
    "investment",
    "order win",
    "dividend",
    "buyback",
    "rating",
)


class NewsToolError(Exception):
    """Base exception for news retrieval and summarization failures."""


class MissingNewsApiKeyError(NewsToolError):
    """Raised when the NewsAPI key is missing."""


class InvalidCompanyNameError(NewsToolError):
    """Raised when the requested company name is empty or invalid."""


class NewsApiError(NewsToolError):
    """Raised when NewsAPI returns an error or cannot be reached."""


class NewsApiRateLimitError(NewsApiError):
    """Raised when NewsAPI rate limits the request."""


class EmptyNewsResponseError(NewsToolError):
    """Raised when no useful articles are available after filtering."""


class GeminiSummarizationError(NewsToolError):
    """Raised when Gemini summarization fails."""


class NewsSummarizer(Protocol):
    """Protocol for a component that summarizes company news articles."""

    def summarize(self, company_name: str, articles: Sequence[NewsArticle]) -> NewsSummary:
        """Summarize material company news articles."""


class NewsApiTool:
    """Retrieve, deduplicate, and filter company news from NewsAPI or public RSS."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        session: requests.Session | None = None,
        endpoint: str = NEWS_API_ENDPOINT,
    ) -> None:
        """Initialize the news tool with injectable HTTP dependencies."""
        load_dotenv()
        self._api_key = api_key or os.getenv("NEWS_API_KEY")
        self._session = session or requests.Session()
        self._endpoint = endpoint

    def fetch_company_news(
        self,
        company_name: str,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Fetch recent company news.

        NewsAPI is used when configured. Without a key, the tool falls back to
        Google News RSS so a local judge demo still has live news capability.
        """
        normalized_company_name = self._validate_company_name(company_name)
        normalized_to_date = to_date or datetime.now(UTC).date()
        normalized_from_date = from_date or normalized_to_date - timedelta(days=30)
        normalized_limit = self._validate_limit(limit)

        logger.info(
            "Fetching news company=%s from_date=%s to_date=%s limit=%s source=%s",
            normalized_company_name,
            normalized_from_date,
            normalized_to_date,
            normalized_limit,
            "newsapi" if self._api_key else "google_news_rss",
        )

        if self._api_key:
            payload = self._request_newsapi(
                normalized_company_name,
                normalized_from_date,
                normalized_to_date,
                normalized_limit,
            )
            raw_articles = payload.get("articles", [])
            if not isinstance(raw_articles, list):
                logger.warning("NewsAPI returned non-list articles payload")
                raise NewsApiError("NewsAPI returned an invalid articles payload.")
            articles = self._normalize_newsapi_articles(raw_articles)
        else:
            articles = self._request_google_news_rss(
                normalized_company_name,
                normalized_from_date,
                normalized_to_date,
                normalized_limit,
            )

        articles = self._deduplicate_articles(articles)
        articles = self._filter_relevant_articles(normalized_company_name, articles)
        articles = articles[:normalized_limit]

        if not articles:
            logger.warning("No useful news articles found company=%s", normalized_company_name)
            raise EmptyNewsResponseError(f"No useful news articles found for '{normalized_company_name}'.")

        logger.info("Fetched news company=%s filtered_count=%s", normalized_company_name, len(articles))
        return articles

    def _request_newsapi(self, company_name: str, from_date: date, to_date: date, limit: int) -> Mapping[str, Any]:
        """Execute the NewsAPI request and validate the response."""
        params = {
            "q": company_name,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(limit * 2, 100),
            "apiKey": self._api_key,
        }
        try:
            response = self._session.get(self._endpoint, params=params, timeout=15)
        except requests.RequestException as exc:
            logger.exception("NewsAPI request failed company=%s", company_name)
            raise NewsApiError("Unable to reach NewsAPI.") from exc

        if response.status_code == 429:
            logger.warning("NewsAPI rate limit reached company=%s", company_name)
            raise NewsApiRateLimitError("NewsAPI rate limit reached.")
        if response.status_code >= 400:
            logger.warning("NewsAPI HTTP error company=%s status_code=%s", company_name, response.status_code)
            raise NewsApiError(f"NewsAPI returned HTTP {response.status_code}.")

        try:
            payload = response.json()
        except ValueError as exc:
            logger.exception("NewsAPI returned invalid JSON company=%s", company_name)
            raise NewsApiError("NewsAPI returned invalid JSON.") from exc

        if payload.get("status") != "ok":
            message = payload.get("message", "NewsAPI returned an error response.")
            logger.warning("NewsAPI error company=%s message=%s", company_name, message)
            raise NewsApiError(str(message))
        return payload

    def _request_google_news_rss(
        self,
        company_name: str,
        from_date: date,
        to_date: date,
        limit: int,
    ) -> list[NewsArticle]:
        """Fetch news from Google News RSS without requiring credentials."""
        query = quote_plus(f'"{company_name}" when:{max(1, (to_date - from_date).days)}d')
        url = f"{GOOGLE_NEWS_RSS_ENDPOINT}?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            response = self._session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Google News RSS request failed company=%s", company_name)
            raise NewsApiError("Unable to reach Google News RSS fallback.") from exc

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            logger.exception("Google News RSS returned invalid XML company=%s", company_name)
            raise NewsApiError("Google News RSS returned invalid XML.") from exc

        articles: list[NewsArticle] = []
        for item in root.findall("./channel/item")[: min(limit * 2, 50)]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            source = (item.findtext("source") or "Google News").strip()
            pub_date = self._parse_rss_date(item.findtext("pubDate"))
            description = self._strip_html(item.findtext("description") or title)
            if not title or not link:
                continue
            try:
                articles.append(
                    NewsArticle(
                        title=title,
                        source=source,
                        publication_date=pub_date,
                        description=description,
                        url=link,
                    )
                )
            except Exception:
                logger.debug("Skipping malformed RSS article", exc_info=True)
        return articles

    def _normalize_newsapi_articles(self, raw_articles: Sequence[Mapping[str, Any]]) -> list[NewsArticle]:
        """Convert NewsAPI article dictionaries into validated NewsArticle models."""
        normalized_articles: list[NewsArticle] = []
        for raw_article in raw_articles:
            try:
                title = str(raw_article.get("title") or "").strip()
                source_payload = raw_article.get("source") or {}
                source = str(source_payload.get("name") or "Unknown").strip()
                published_at = self._parse_publication_date(raw_article.get("publishedAt"))
                article = NewsArticle(
                    title=title,
                    source=source,
                    publication_date=published_at,
                    description=raw_article.get("description"),
                    url=raw_article.get("url"),
                )
            except Exception:
                logger.debug("Skipping malformed NewsAPI article", exc_info=True)
                continue
            normalized_articles.append(article)
        return normalized_articles

    def _deduplicate_articles(self, articles: Sequence[NewsArticle]) -> list[NewsArticle]:
        """Remove duplicate articles using URL first and normalized title second."""
        seen_keys: set[str] = set()
        unique_articles: list[NewsArticle] = []
        for article in articles:
            key = str(article.url).lower().rstrip("/") or article.title.lower()
            title_key = article.title.lower().strip()
            if key in seen_keys or title_key in seen_keys:
                continue
            seen_keys.add(key)
            seen_keys.add(title_key)
            unique_articles.append(article)
        return unique_articles

    def _filter_relevant_articles(self, company_name: str, articles: Sequence[NewsArticle]) -> list[NewsArticle]:
        """Filter articles that lack company relevance or useful information."""
        company_tokens = {
            token.lower()
            for token in company_name.replace(".", " ").replace("-", " ").split()
            if len(token) >= 2
        }
        relevant_articles: list[NewsArticle] = []
        for article in articles:
            combined_text = f"{article.title} {article.description or ''}".lower()
            has_company_match = any(token in combined_text for token in company_tokens)
            has_material_keyword = any(keyword in combined_text for keyword in MATERIAL_EVENT_KEYWORDS)
            has_enough_information = len(combined_text.split()) >= 5
            if has_enough_information and (has_company_match or has_material_keyword):
                relevant_articles.append(article)
        return relevant_articles

    def _validate_company_name(self, company_name: str) -> str:
        """Validate and normalize the company search string."""
        if not company_name or not company_name.strip():
            logger.warning("Blank company name received")
            raise InvalidCompanyNameError("Company name must not be empty.")
        return company_name.strip()

    def _validate_api_key(self) -> None:
        """Ensure a NewsAPI key is available."""
        if not self._api_key:
            logger.warning("NEWS_API_KEY is missing")
            raise MissingNewsApiKeyError("NEWS_API_KEY must be set in .env.")

    def _validate_limit(self, limit: int) -> int:
        """Validate and normalize the article result limit."""
        if limit < 1:
            raise ValueError("limit must be greater than zero.")
        return min(limit, 100)

    def _parse_publication_date(self, value: Any) -> datetime:
        """Parse NewsAPI publishedAt values into timezone-aware datetimes."""
        if not value:
            raise ValueError("publishedAt is required.")
        normalized_value = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized_value)

    def _parse_rss_date(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    def _strip_html(self, value: str) -> str:
        return " ".join(value.replace("<ol>", " ").replace("</ol>", " ").split())


class ExtractiveNewsSummarizer:
    """Fast local summarizer for no-key demos."""

    def summarize(self, company_name: str, articles: Sequence[NewsArticle]) -> NewsSummary:
        if not articles:
            raise GeminiSummarizationError("At least one article is required for summarization.")
        sorted_articles = sorted(articles, key=self._materiality_score, reverse=True)
        top_articles = sorted_articles[:5]
        material_events = [f"{article.title} ({article.source})" for article in top_articles[:4]]
        summary = (
            f"Recent coverage for {company_name} includes {len(articles)} relevant articles. "
            f"Most material headlines: " + "; ".join(material_events[:3]) + "."
        )
        return NewsSummary(
            summary=summary,
            material_events=material_events,
            limitations=["Generated with local extractive summarization; verify full articles before investment use."],
        )

    def _materiality_score(self, article: NewsArticle) -> int:
        combined = f"{article.title} {article.description or ''}".lower()
        return sum(2 for keyword in MATERIAL_EVENT_KEYWORDS if keyword in combined) + len(combined.split()) // 20


class GeminiNewsSummarizer:
    """Summarize material news developments using Gemini."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash") -> None:
        """Initialize the Gemini summarizer with environment-based configuration."""
        load_dotenv()
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name

    def summarize(self, company_name: str, articles: Sequence[NewsArticle]) -> NewsSummary:
        """Summarize important company news and material events with Gemini."""
        if not self._api_key:
            logger.warning("GOOGLE_API_KEY is missing")
            raise GeminiSummarizationError("GOOGLE_API_KEY must be set in .env.")
        if not articles:
            raise GeminiSummarizationError("At least one article is required for summarization.")

        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model_name)
            response = model.generate_content(self._build_prompt(company_name, articles))
            text = getattr(response, "text", None)
        except Exception as exc:
            logger.exception("Gemini summarization failed company=%s", company_name)
            raise GeminiSummarizationError("Gemini failed to summarize news.") from exc

        if not text or not text.strip():
            logger.warning("Gemini returned an empty summary company=%s", company_name)
            raise GeminiSummarizationError("Gemini returned an empty summary.")
        return self._parse_summary_text(text)

    def _build_prompt(self, company_name: str, articles: Sequence[NewsArticle]) -> str:
        """Build a compact Gemini prompt from normalized articles."""
        article_lines = []
        for index, article in enumerate(articles, start=1):
            article_lines.append(
                "\n".join(
                    [
                        f"{index}. Title: {article.title}",
                        f"Source: {article.source}",
                        f"Date: {article.publication_date.date().isoformat()}",
                        f"Description: {article.description or 'N/A'}",
                        f"URL: {article.url}",
                    ]
                )
            )

        return (
            "You are a financial research assistant. Summarize material news for "
            f"{company_name}. Focus on major contracts, acquisitions, leadership changes, "
            "earnings announcements, regulatory actions, litigation, and strategic partnerships. "
            "Return strict JSON with keys summary, material_events, and limitations. "
            "material_events and limitations must be arrays of strings.\n\n"
            + "\n\n".join(article_lines)
        )

    def _parse_summary_text(self, text: str) -> NewsSummary:
        """Parse Gemini JSON output, falling back to plain text when needed."""
        cleaned_text = text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
            cleaned_text = cleaned_text.removeprefix("json").strip()
        try:
            payload = json.loads(cleaned_text)
        except json.JSONDecodeError:
            return NewsSummary(
                summary=cleaned_text,
                material_events=[],
                limitations=["Gemini returned non-JSON text; parsed as plain summary."],
            )

        return NewsSummary(
            summary=str(payload.get("summary", "")).strip(),
            material_events=[str(item) for item in payload.get("material_events", [])],
            limitations=[str(item) for item in payload.get("limitations", [])],
        )


def fetch_company_news(
    company_name: str,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 20,
) -> list[NewsArticle]:
    """Convenience function for retrieving company news with the default tool."""
    return NewsApiTool().fetch_company_news(company_name, from_date, to_date, limit)
