"""Peer Comparison Agent."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol

from agents.peer_agent.models import PeerComparisonResponse
from tools.peer_tools import PeerComparisonError, PeerComparisonTool

logger = logging.getLogger(__name__)


class PeerComparisonProvider(Protocol):
    """Protocol for peer comparison tools."""

    def compare_peers(
        self,
        target_ticker: str,
        peer_tickers: Sequence[str] | None = None,
    ) -> PeerComparisonResponse:
        """Compare a target company with peer tickers."""


class PeerComparisonAgent:
    """Agent responsible for peer comparison orchestration."""

    def __init__(self, peer_tool: PeerComparisonProvider | None = None) -> None:
        """Initialize the agent with an injectable peer comparison tool."""
        self._peer_tool = peer_tool or PeerComparisonTool()

    def compare_peers(
        self,
        target_ticker: str,
        peer_tickers: Sequence[str] | None = None,
    ) -> PeerComparisonResponse:
        """Compare a target company against peers.

        Args:
            target_ticker: Target company ticker.
            peer_tickers: Optional explicit peer universe.

        Raises:
            PeerComparisonError: When peer identification or comparison fails.
        """
        logger.info("PeerComparisonAgent started target=%s", target_ticker)
        try:
            response = self._peer_tool.compare_peers(target_ticker, peer_tickers)
        except PeerComparisonError:
            logger.exception("PeerComparisonAgent failed target=%s", target_ticker)
            raise

        logger.info(
            "PeerComparisonAgent completed target=%s peer_count=%s unavailable=%s",
            response.target_ticker,
            len(response.peers),
            response.unavailable_tickers,
        )
        return response


def compare_peers(
    target_ticker: str,
    peer_tickers: Sequence[str] | None = None,
) -> PeerComparisonResponse:
    """Convenience function for comparing peers."""
    return PeerComparisonAgent().compare_peers(target_ticker, peer_tickers)
