"""Tools for identifying and comparing peer companies."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Protocol

from agents.financial_agent.models import FinancialAnalysis
from agents.peer_agent.models import PeerComparisonResponse, PeerComparisonTable, PeerMetrics, PeerRank
from tools.financial_tools import FinancialDataError, FinancialDataTool

logger = logging.getLogger(__name__)

CURATED_PEER_UNIVERSES: Mapping[str, tuple[str, ...]] = {
    # Indian IT services, the most likely contest/demo universe.
    "TCS.NS": ("INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIMINDTREE.NS"),
    "INFY.NS": ("TCS.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIMINDTREE.NS"),
    "WIPRO.NS": ("TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS", "LTIMINDTREE.NS"),
    "HCLTECH.NS": ("TCS.NS", "INFY.NS", "WIPRO.NS", "TECHM.NS", "LTIMINDTREE.NS"),
    "TECHM.NS": ("TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "LTIMINDTREE.NS"),
    "LTIMINDTREE.NS": ("TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"),
    # Indian banks and financials.
    "HDFCBANK.NS": ("ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"),
    "ICICIBANK.NS": ("HDFCBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"),
    "SBIN.NS": ("HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "BANKBARODA.NS"),
    "RELIANCE.NS": ("ONGC.NS", "IOC.NS", "BPCL.NS", "HINDPETRO.NS", "ADANIENT.NS"),
    "ITC.NS": ("HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS", "MARICO.NS"),
    "TATAMOTORS.NS": ("M&M.NS", "MARUTI.NS", "EICHERMOT.NS", "BAJAJ-AUTO.NS", "ASHOKLEY.NS"),
    # US large-cap demos.
    "MSFT": ("AAPL", "GOOGL", "AMZN", "META", "ORCL"),
    "AAPL": ("MSFT", "GOOGL", "AMZN", "META", "NVDA"),
    "GOOGL": ("MSFT", "AAPL", "META", "AMZN", "NFLX"),
    "AMZN": ("MSFT", "AAPL", "GOOGL", "WMT", "META"),
    "NVDA": ("AMD", "INTC", "AVGO", "QCOM", "TSM"),
    "TSLA": ("GM", "F", "RIVN", "NIO", "TM"),
}

SECTOR_FALLBACK_PEERS: Mapping[str, tuple[str, ...]] = {
    "technology": ("MSFT", "AAPL", "GOOGL", "META", "ORCL"),
    "information technology": ("TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"),
    "financial": ("HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"),
    "bank": ("HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"),
    "consumer": ("ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"),
    "auto": ("TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "EICHERMOT.NS", "BAJAJ-AUTO.NS"),
    "energy": ("RELIANCE.NS", "ONGC.NS", "IOC.NS", "BPCL.NS", "HINDPETRO.NS"),
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
        target_analysis: FinancialAnalysis | None = None
        unavailable_tickers: list[str] = []

        try:
            target_analysis = self._financial_data_provider.get_financial_analysis(normalized_target)
        except FinancialDataError:
            logger.exception("Target financial data unavailable ticker=%s", normalized_target)
            unavailable_tickers.append(normalized_target)

        resolved_peer_tickers = self.identify_peers(normalized_target, peer_tickers, target_analysis)
        logger.info("Starting peer comparison target=%s peers=%s", normalized_target, resolved_peer_tickers)

        peers: list[PeerMetrics] = []
        if target_analysis is not None:
            peers.append(self._to_peer_metrics(target_analysis))

        for ticker in resolved_peer_tickers:
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
        target_analysis: FinancialAnalysis | None = None,
    ) -> list[str]:
        """Return explicit, curated, or sector-inferred peers."""
        normalized_target = self._normalize_ticker(target_ticker)
        if peer_tickers is not None:
            return self._dedupe_peer_tickers(normalized_target, peer_tickers)

        if normalized_target in CURATED_PEER_UNIVERSES:
            return list(CURATED_PEER_UNIVERSES[normalized_target])

        inferred = self._infer_peers_from_company_profile(normalized_target, target_analysis)
        if inferred:
            return inferred

        raise InvalidPeerInputError(
            f"No peer universe configured for '{normalized_target}'. Provide --peer-tickers for custom companies."
        )

    def _infer_peers_from_company_profile(
        self,
        normalized_target: str,
        target_analysis: FinancialAnalysis | None,
    ) -> list[str]:
        """Infer a reasonable peer universe from sector and industry metadata."""
        if target_analysis is None:
            return []
        profile_text = " ".join(
            part.lower()
            for part in [target_analysis.company.sector, target_analysis.company.industry]
            if part
        )
        for keyword, peers in SECTOR_FALLBACK_PEERS.items():
            if keyword in profile_text:
                return self._dedupe_peer_tickers(normalized_target, peers)
        return []

    def _dedupe_peer_tickers(self, normalized_target: str, peer_tickers: Sequence[str]) -> list[str]:
        normalized_peers = [self._normalize_ticker(ticker) for ticker in peer_tickers]
        unique_peers = []
        for ticker in normalized_peers:
            if ticker != normalized_target and ticker not in unique_peers:
                unique_peers.append(ticker)
        if not unique_peers:
            raise InvalidPeerInputError("At least one peer ticker different from target is required.")
        return unique_peers

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
            available_values = [(peer.ticker, getattr(peer, metric)) for peer in peers if getattr(peer, metric) is not None]
            sorted_values = sorted(available_values, key=lambda item: item[1], reverse=higher_is_better)
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


def compare_peers(target_ticker: str, peer_tickers: Sequence[str] | None = None) -> PeerComparisonResponse:
    """Convenience function for peer comparison with the default tool."""
    return PeerComparisonTool().compare_peers(target_ticker, peer_tickers)
