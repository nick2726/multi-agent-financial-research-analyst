"""Tests for the Peer Comparison Agent."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from agents.peer_agent.models import PeerComparisonResponse, PeerComparisonTable, PeerMetrics
from agents.peer_agent.peer_agent import PeerComparisonAgent
from tools.peer_tools import InvalidPeerInputError


class FakePeerTool:
    """Peer comparison fake for agent orchestration tests."""

    def __init__(self, response: PeerComparisonResponse | None = None) -> None:
        """Create the fake peer tool with an optional response."""
        self.response = response
        self.received_target_ticker: str | None = None
        self.received_peer_tickers: Sequence[str] | None = None

    def compare_peers(
        self,
        target_ticker: str,
        peer_tickers: Sequence[str] | None = None,
    ) -> PeerComparisonResponse:
        """Return a fixed response and record arguments."""
        self.received_target_ticker = target_ticker
        self.received_peer_tickers = peer_tickers
        if self.response is None:
            raise InvalidPeerInputError("invalid input")
        return self.response


def _response() -> PeerComparisonResponse:
    """Build a peer comparison response fixture."""
    peers = [
        PeerMetrics(
            ticker="INFY.NS",
            company_name="INFY.NS Limited",
            market_cap=10_000,
            pe_ratio=25,
            revenue_growth=0.12,
            operating_margin=0.24,
            roe=0.30,
            eps=60,
        )
    ]
    return PeerComparisonResponse(
        target_ticker="INFY.NS",
        peer_tickers=["TCS.NS"],
        peers=peers,
        rankings=[],
        comparison_table=PeerComparisonTable(
            columns=["ticker", "company_name"],
            rows=[{"ticker": "INFY.NS", "company_name": "INFY.NS Limited"}],
        ),
    )


def test_peer_agent_delegates_to_peer_tool() -> None:
    """PeerComparisonAgent should delegate comparison to the injected tool."""
    tool = FakePeerTool(response=_response())

    response = PeerComparisonAgent(peer_tool=tool).compare_peers("infy.ns", ["tcs.ns"])

    assert tool.received_target_ticker == "infy.ns"
    assert tool.received_peer_tickers == ["tcs.ns"]
    assert response.target_ticker == "INFY.NS"
    assert response.peer_tickers == ["TCS.NS"]


def test_peer_agent_propagates_tool_failures() -> None:
    """PeerComparisonAgent should not hide peer comparison failures."""
    agent = PeerComparisonAgent(peer_tool=FakePeerTool(response=None))

    with pytest.raises(InvalidPeerInputError):
        agent.compare_peers(" ")
