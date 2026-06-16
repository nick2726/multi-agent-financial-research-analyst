"""Pydantic models for company news analysis."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class NewsArticle(BaseModel):
    """Normalized news article returned by the NewsAPI tool."""

    title: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    publication_date: datetime
    description: Optional[str] = None
    url: HttpUrl

    @field_validator("title", "source")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Strip required text fields before validation."""
        return value.strip()

    @field_validator("description")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """Normalize optional text fields."""
        if value is None:
            return None
        stripped_value = value.strip()
        return stripped_value or None


class NewsSummary(BaseModel):
    """Gemini-generated summary of material company news."""

    summary: str
    material_events: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class NewsAgentResponse(BaseModel):
    """Structured response produced by the News Agent."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    query: str
    from_date: date
    to_date: date
    articles: list[NewsArticle]
    summary: NewsSummary
    source: str = "NewsAPI"
