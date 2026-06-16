"""Tools for identifying and comparing peer companies."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Protocol

from agents.financial_agent.models import FinancialAnalysis
from agents.peer_agent.models import PeerComparisonResponse, PeerComparisonTable, PeerMetrics, PeerRank
from tools.financial_tools import FinancialDataError, FinancialDataTool

logger = logging.getLogger(__name__)

DEFAULT_INDIAN_IT_PEERS: Mapping[str, tuple[str, ...]] = {
    "TCS.NS": ("INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"),
    "INFY.NS": ("TCS.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"),
    "WIPRO.NS": ("TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"),
    "HCLTECH.NS": ("TCS.NS", "INFY.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS"),
    "TECHM.NS": ("TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "LTIM.NS"),
    "LTIM.NS": ("TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"),
}

METRIC_DIRECTIONS: Mapping[str, bool] = {
    "market_cap": True,
    "pe_ratio": False,
    "revenue_growth": True,
    "operating_margin": True,
    "roe": True,
    "eps": True,
}


class PeerComparisonError(Exception):
    """Base exception for peer comparison failures."""


class InvalidPeerInputError(PeerComparisonError):
    """Raised when the requested target or peer inputs are invalid."""


class NoPeerDataError(PeerComparisonError):
    """Raised when no peer data can be retrieved."""


class PeerFinancialDataProvider(Protocol):
    """Protocol for retrieving financial analysis used in peer comparison."""

    def get_financial_analysis(self, ticker: str) -> FinancialAnalysis:
        """Return structured financial analysis for a ticker."""


class PeerComparisonTool:
    """Identify peers and compare valuation metrics."""

    def __init__(self, financial_data_provider: PeerFinancialDataProvider | None = None) -> None:
        """Initialize the tool with an injectable financial data provider."""
        self._financial_data_provider = financial_data_provider or FinancialDataTool()

    def compare_peers(
        self,
        target_ticker: str,
        peer_tickers: Sequence[str] | None = None,
    ) -> PeerComparisonResponse:
        """Compare a target company against peers using financial metrics."""
        normalized_target = self._normalize_ticker(target_ticker)
        resolved_peer_tickers = self.identify_peers(normalized_target, peer_tickers)
        tickers_to_fetch = [normalized_target, *resolved_peer_tickers]
        logger.info(
            "Starting peer comparison target=%s peers=%s",
            normalized_target,
            resolved_peer_tickers,
        )

        peers: list[PeerMetrics] = []
        unavailable_tickers: list[str] = []
        for ticker in tickers_to_fetch:
            try:
                analysis = self._financial_data_provider.get_financial_analysis(ticker)
            except FinancialDataError:
                logger.exception("Peer financial data unavailable ticker=%s", ticker)
                unavailable_tickers.append(ticker)
                continue
            peers.append(self._to_peer_metrics(analysis))

        if not peers:
            logger.warning("No peer data available target=%s", normalized_target)
            raise NoPeerDataError("No financial data was available for the target or peers.")

        rankings = self._rank_peers(peers)
        comparison_table = self._build_comparison_table(peers)
        logger.info(
            "Completed peer comparison target=%s available=%s unavailable=%s",
            normalized_target,
            len(peers),
            unavailable_tickers,
        )
        return PeerComparisonResponse(
            target_ticker=normalized_target,
            peer_tickers=resolved_peer_tickers,
            peers=peers,
            rankings=rankings,
            comparison_table=comparison_table,
            unavailable_tickers=unavailable_tickers,
        )

    def identify_peers(
        self,
        target_ticker: str,
        peer_tickers: Sequence[str] | None = None,
    ) -> list[str]:
        """Return explicit peers or the default Indian IT peer universe."""
        normalized_target = self._normalize_ticker(target_ticker)
        if peer_tickers is not None:
            normalized_peers = [self._normalize_ticker(ticker) for ticker in peer_tickers]
            unique_peers = []
            for ticker in normalized_peers:
                if ticker != normalized_target and ticker not in unique_peers:
                    unique_peers.append(ticker)
            if not unique_peers:
                raise InvalidPeerInputError("At least one peer ticker different from target is required.")
            return unique_peers

        if normalized_target not in DEFAULT_INDIAN_IT_PEERS:
            raise InvalidPeerInputError(
                f"No default Indian IT peer universe configured for '{normalized_target}'."
            )
        return list(DEFAULT_INDIAN_IT_PEERS[normalized_target])

    def _to_peer_metrics(self, analysis: FinancialAnalysis) -> PeerMetrics:
        """Convert financial analysis output into peer comparison metrics."""
        metrics = analysis.metrics
        missing_fields = [
            field_name
            for field_name, value in {
                "market_cap": metrics.market_cap,
                "pe_ratio": metrics.pe_ratio,
                "revenue_growth": metrics.revenue_growth,
                "operating_margin": metrics.operating_margins,
                "roe": metrics.roe,
                "eps": metrics.eps,
            }.items()
            if value is None
        ]
        return PeerMetrics(
            ticker=analysis.company.ticker,
            company_name=analysis.company.name,
            market_cap=metrics.market_cap,
            pe_ratio=metrics.pe_ratio,
            revenue_growth=metrics.revenue_growth,
            operating_margin=metrics.operating_margins,
            roe=metrics.roe,
            eps=metrics.eps,
            missing_fields=missing_fields,
        )

    def _rank_peers(self, peers: Sequence[PeerMetrics]) -> list[PeerRank]:
        """Rank peers for every comparable metric."""
        rankings: list[PeerRank] = []
        for metric, higher_is_better in METRIC_DIRECTIONS.items():
            available_values = [
                (peer.ticker, getattr(peer, metric))
                for peer in peers
                if getattr(peer, metric) is not None
            ]
            sorted_values = sorted(
                available_values,
                key=lambda item: item[1],
                reverse=higher_is_better,
            )
            for index, (ticker, value) in enumerate(sorted_values, start=1):
                rankings.append(PeerRank(ticker=ticker, metric=metric, rank=index, value=value))
        return rankings

    def _build_comparison_table(self, peers: Sequence[PeerMetrics]) -> PeerComparisonTable:
        """Build a serializable comparison table from peer metrics."""
        columns = [
            "ticker",
            "company_name",
            "market_cap",
            "pe_ratio",
            "revenue_growth",
            "operating_margin",
            "roe",
            "eps",
        ]
        rows = [{column: getattr(peer, column) for column in columns} for peer in peers]
        return PeerComparisonTable(columns=columns, rows=rows)

    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize and validate a ticker symbol."""
        if not ticker or not ticker.strip():
            logger.warning("Blank ticker received for peer comparison")
            raise InvalidPeerInputError("Ticker must not be empty.")
        return ticker.strip().upper()


def compare_peers(
    target_ticker: str,
    peer_tickers: Sequence[str] | None = None,
) -> PeerComparisonResponse:
    """Convenience function for peer comparison with the default tool."""
    return PeerComparisonTool().compare_peers(target_ticker, peer_tickers)
