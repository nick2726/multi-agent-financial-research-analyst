"""Tools for retrieving financial data from yfinance.

Agents should depend on this module instead of calling yfinance directly.
That separation keeps external API concerns testable and replaceable.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Optional

import pandas as pd
import yfinance as yf

from agents.financial_agent.models import CompanyInfo, FinancialAnalysis, FinancialMetrics

logger = logging.getLogger(__name__)


class FinancialDataError(Exception):
    """Base exception for financial data retrieval failures."""


class InvalidTickerError(FinancialDataError):
    """Raised when a ticker symbol is empty, invalid, or unsupported."""


class MissingFinancialDataError(FinancialDataError):
    """Raised when yfinance returns too little data for analysis."""


class FinancialDataSourceError(FinancialDataError):
    """Raised when the upstream financial data source fails."""


class FinancialDataTool:
    """Retrieve and normalize company financial data from yfinance."""

    def get_financial_analysis(self, ticker: str) -> FinancialAnalysis:
        """Return normalized company information and financial metrics.

        Args:
            ticker: Exchange ticker symbol accepted by yfinance.

        Raises:
            InvalidTickerError: If the ticker is blank or yfinance has no company data.
            MissingFinancialDataError: If no useful financial metrics are available.
            FinancialDataSourceError: If yfinance or the network fails unexpectedly.
        """
        normalized_ticker = self._validate_ticker(ticker)
        logger.info("Fetching financial data for ticker=%s", normalized_ticker)

        try:
            yfinance_ticker = yf.Ticker(normalized_ticker)
            info = self._get_info(yfinance_ticker, normalized_ticker)
            financials = self._safe_dataframe(yfinance_ticker, "financials")
            balance_sheet = self._safe_dataframe(yfinance_ticker, "balance_sheet")
        except InvalidTickerError:
            raise
        except FinancialDataError:
            raise
        except Exception as exc:
            logger.exception("Unexpected yfinance failure for ticker=%s", normalized_ticker)
            raise FinancialDataSourceError(
                f"Failed to retrieve financial data for ticker '{normalized_ticker}'."
            ) from exc

        company = self._build_company_info(normalized_ticker, info)
        metrics = self._build_financial_metrics(info, financials, balance_sheet)
        missing_fields = self._missing_metric_fields(metrics)

        if len(missing_fields) == len(FinancialMetrics.model_fields):
            logger.warning("No usable financial metrics found for ticker=%s", normalized_ticker)
            raise MissingFinancialDataError(
                f"No usable financial metrics found for ticker '{normalized_ticker}'."
            )

        logger.info(
            "Completed financial data retrieval for ticker=%s missing_fields=%s",
            normalized_ticker,
            missing_fields,
        )
        return FinancialAnalysis(
            company=company,
            metrics=metrics,
            missing_fields=missing_fields,
        )

    def _validate_ticker(self, ticker: str) -> str:
        """Validate and normalize the requested ticker symbol."""
        if not ticker or not ticker.strip():
            logger.warning("Blank ticker symbol received")
            raise InvalidTickerError("Ticker symbol must not be empty.")
        return ticker.strip().upper()

    def _get_info(self, yfinance_ticker: yf.Ticker, ticker: str) -> Mapping[str, Any]:
        """Return the yfinance info dictionary and validate ticker existence."""
        try:
            info = yfinance_ticker.info
        except Exception as exc:
            logger.exception("Failed to read yfinance info for ticker=%s", ticker)
            raise FinancialDataSourceError(
                f"Unable to retrieve company information for ticker '{ticker}'."
            ) from exc

        if not isinstance(info, Mapping) or not info:
            logger.warning("Empty yfinance info returned for ticker=%s", ticker)
            raise InvalidTickerError(f"Ticker '{ticker}' was not found.")

        has_identity = bool(info.get("shortName") or info.get("longName"))
        has_quote_type = bool(info.get("quoteType"))
        if not has_identity and not has_quote_type:
            logger.warning("Invalid yfinance info payload for ticker=%s", ticker)
            raise InvalidTickerError(f"Ticker '{ticker}' was not found.")

        return info

    def _safe_dataframe(self, yfinance_ticker: yf.Ticker, attribute_name: str) -> pd.DataFrame:
        """Read a yfinance DataFrame attribute and convert failures into tool errors."""
        try:
            value = getattr(yfinance_ticker, attribute_name)
        except Exception as exc:
            logger.exception("Failed to read yfinance attribute=%s", attribute_name)
            raise FinancialDataSourceError(
                f"Unable to retrieve yfinance attribute '{attribute_name}'."
            ) from exc

        if isinstance(value, pd.DataFrame):
            return value
        logger.warning("Expected DataFrame for attribute=%s but received %s", attribute_name, type(value))
        return pd.DataFrame()

    def _build_company_info(self, ticker: str, info: Mapping[str, Any]) -> CompanyInfo:
        """Build company metadata from a yfinance info payload."""
        company_name = self._first_present(info, "longName", "shortName", default=ticker)
        return CompanyInfo(
            ticker=ticker,
            name=str(company_name),
            sector=self._to_optional_string(info.get("sector")),
            industry=self._to_optional_string(info.get("industry")),
            country=self._to_optional_string(info.get("country")),
            currency=self._to_optional_string(info.get("currency")),
            exchange=self._to_optional_string(info.get("exchange")),
        )

    def _build_financial_metrics(
        self,
        info: Mapping[str, Any],
        financials: pd.DataFrame,
        balance_sheet: pd.DataFrame,
    ) -> FinancialMetrics:
        """Build the normalized financial metrics model."""
        revenue = self._first_numeric(
            info,
            "totalRevenue",
            fallback=self._latest_statement_value(financials, "Total Revenue"),
        )
        net_income = self._first_numeric(
            info,
            "netIncomeToCommon",
            fallback=self._latest_statement_value(financials, "Net Income"),
        )
        return FinancialMetrics(
            revenue=revenue,
            net_income=net_income,
            eps=self._first_numeric(info, "trailingEps", "forwardEps"),
            pe_ratio=self._first_numeric(info, "trailingPE", "forwardPE"),
            market_cap=self._first_numeric(info, "marketCap"),
            revenue_growth=self._calculate_revenue_growth(info, financials),
            operating_margins=self._first_numeric(info, "operatingMargins"),
            roe=self._calculate_roe(info, net_income, balance_sheet),
        )

    def _calculate_revenue_growth(
        self,
        info: Mapping[str, Any],
        financials: pd.DataFrame,
    ) -> Optional[float]:
        """Calculate revenue growth from statements, falling back to yfinance info."""
        statement_revenues = self._statement_row_values(financials, "Total Revenue")
        if len(statement_revenues) >= 2 and statement_revenues[1] != 0:
            return (statement_revenues[0] - statement_revenues[1]) / abs(statement_revenues[1])
        return self._first_numeric(info, "revenueGrowth")

    def _calculate_roe(
        self,
        info: Mapping[str, Any],
        net_income: Optional[float],
        balance_sheet: pd.DataFrame,
    ) -> Optional[float]:
        """Calculate return on equity when yfinance does not provide it directly."""
        direct_roe = self._first_numeric(info, "returnOnEquity")
        if direct_roe is not None:
            return direct_roe

        shareholder_equity = self._latest_statement_value(
            balance_sheet,
            "Stockholders Equity",
            "Total Stockholder Equity",
            "Common Stock Equity",
        )
        if net_income is None or shareholder_equity in (None, 0):
            return None
        return net_income / shareholder_equity

    def _latest_statement_value(self, dataframe: pd.DataFrame, *row_names: str) -> Optional[float]:
        """Return the most recent numeric value for any matching statement row."""
        values = self._statement_row_values(dataframe, *row_names)
        return values[0] if values else None

    def _statement_row_values(self, dataframe: pd.DataFrame, *row_names: str) -> list[float]:
        """Return numeric values from the first matching financial statement row."""
        if dataframe.empty:
            return []

        for row_name in row_names:
            if row_name in dataframe.index:
                row = pd.to_numeric(dataframe.loc[row_name], errors="coerce").dropna()
                return [float(value) for value in row.tolist()]
        return []

    def _missing_metric_fields(self, metrics: FinancialMetrics) -> list[str]:
        """Return names of metrics that could not be retrieved or calculated."""
        return [
            field_name
            for field_name, value in metrics.model_dump().items()
            if value is None
        ]

    def _first_numeric(
        self,
        info: Mapping[str, Any],
        *keys: str,
        fallback: Optional[float] = None,
    ) -> Optional[float]:
        """Return the first numeric value from the info payload or a fallback."""
        for key in keys:
            value = info.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and pd.notna(value):
                return float(value)
        return fallback

    def _first_present(
        self,
        info: Mapping[str, Any],
        *keys: str,
        default: str,
    ) -> Any:
        """Return the first truthy value from a mapping."""
        for key in keys:
            value = info.get(key)
            if value:
                return value
        return default

    def _to_optional_string(self, value: Any) -> Optional[str]:
        """Convert optional metadata fields to strings without leaking null-like values."""
        if value is None:
            return None
        return str(value)


def get_financial_analysis(ticker: str) -> FinancialAnalysis:
    """Convenience function for retrieving financial analysis with the default tool."""
    return FinancialDataTool().get_financial_analysis(ticker)
