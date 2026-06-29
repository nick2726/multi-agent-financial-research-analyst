#!/usr/bin/env python3
"""CLI runner for Multi-Agent Financial Research Analyst."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

# Ensure the project root is in the path.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from adk.main import run_adk_research
from agents.coordinator.coordinator_agent import CoordinatorAgent
from observability.logging_config import configure_logging


def print_section(title: str) -> None:
    """Render a visible section separator in CLI output."""
    print("\n" + "=" * 60)
    print(f" {title.upper()} ")
    print("=" * 60)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for coordinator and ADK workflows."""
    parser = argparse.ArgumentParser(description="Run Multi-Agent Financial Research Analyst.")
    parser.add_argument("ticker", type=str, nargs="?", default="MSFT", help="Ticker symbol to analyze")
    parser.add_argument("--company-name", type=str, default=None, help="Optional explicit company name")
    parser.add_argument("--filing-path", type=str, default=None, help="Path to current filing PDF")
    parser.add_argument("--previous-filing-path", type=str, default=None, help="Path to previous filing PDF")
    parser.add_argument("--peer-tickers", nargs="*", default=None, help="Optional explicit peer universe")
    parser.add_argument("--no-news", action="store_true", help="Skip news analysis")
    parser.add_argument("--no-peers", action="store_true", help="Skip peer comparison")
    parser.add_argument("--skip-thesis", action="store_true", help="Skip thesis writer agent")
    parser.add_argument("--use-adk", action="store_true", help="Run via ADK wrapper pipeline")
    parser.add_argument("--session-id", type=str, default=None, help="Session id for ADK mode")
    parser.add_argument(
        "--save-output",
        action="store_true",
        help="Persist full response JSON to outputs/ for replay and evaluation",
    )
    return parser.parse_args()


def persist_output_json(response_payload: dict[str, object], ticker: str) -> Path:
    """Persist one response payload for later evaluation and auditability."""
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{timestamp}_{ticker}.json"
    output_path.write_text(json.dumps(response_payload, indent=2), encoding="utf-8")
    return output_path


def print_execution_summary(response, session_id: str | None = None) -> None:
    """Print execution-level coordinator metadata."""
    print_section("Execution Summary")
    print(f"Target Ticker:      {response.request.ticker}")
    if session_id:
        print(f"ADK Session ID:     {session_id}")
    print(f"Completed Agents:   {', '.join(response.completed_agents) if response.completed_agents else 'None'}")
    print(f"Failed Agents:      {', '.join(response.failed_agents) if response.failed_agents else 'None'}")

    if response.execution_metadata:
        print("\nDetails:")
        for meta in response.execution_metadata:
            status_symbol = "OK" if meta.status == "completed" else "FAIL"
            error_msg = f" - Error: {meta.error_type}: {meta.error_message}" if meta.error_message else ""
            print(f"  [{status_symbol}] {meta.agent_name} ({meta.duration_ms:.2f}ms){error_msg}")


def print_financial(data) -> None:
    """Print financial analysis section."""
    if not data.financial_analysis:
        return
    print_section("Company Profile & Financials")
    comp = data.financial_analysis.company
    metrics = data.financial_analysis.metrics

    print(f"Company Name:  {comp.name}")
    print(f"Sector:        {comp.sector or 'N/A'}")
    print(f"Industry:      {comp.industry or 'N/A'}")
    print(f"Exchange:      {comp.exchange or 'N/A'} ({comp.currency or 'USD'})")
    print(f"Country:       {comp.country or 'N/A'}")
    print("-" * 40)
    print("Key Metrics:")
    print(f"  Market Cap:        {metrics.market_cap:,.0f}" if metrics.market_cap is not None else "  Market Cap:        N/A")
    print(f"  Revenue:           {metrics.revenue:,.0f}" if metrics.revenue is not None else "  Revenue:           N/A")
    print(f"  Net Income:        {metrics.net_income:,.0f}" if metrics.net_income is not None else "  Net Income:        N/A")
    print(f"  P/E Ratio:         {metrics.pe_ratio:.2f}" if metrics.pe_ratio is not None else "  P/E Ratio:         N/A")
    print(f"  EPS:               {metrics.eps:.2f}" if metrics.eps is not None else "  EPS:               N/A")
    print(
        f"  Operating Margin:  {metrics.operating_margins * 100:.2f}%"
        if metrics.operating_margins is not None
        else "  Operating Margin:  N/A"
    )
    print(f"  Return on Equity:  {metrics.roe * 100:.2f}%" if metrics.roe is not None else "  Return on Equity:  N/A")
    print(
        f"  Revenue Growth:    {metrics.revenue_growth * 100:.2f}%"
        if metrics.revenue_growth is not None
        else "  Revenue Growth:    N/A"
    )
    if data.financial_analysis.missing_fields:
        print(f"Missing Fields:      {', '.join(data.financial_analysis.missing_fields)}")


def print_peers(data) -> None:
    """Print peer comparison section."""
    if not data.peer_comparison:
        return

    print_section("Peer Comparison")
    pc = data.peer_comparison
    print(f"Peers Compared: {', '.join(pc.peer_tickers)}")
    if pc.comparison_table and pc.comparison_table.rows:
        rows = pc.comparison_table.rows
        cols = pc.comparison_table.columns
        col_widths: dict[str, int] = {}
        for col in cols:
            max_w = len(col)
            for row in rows:
                val = str(row.get(col, ""))
                if len(val) > max_w:
                    max_w = len(val)
            col_widths[col] = max_w + 2

        header_str = "".join(f"{col:<{col_widths[col]}}" for col in cols)
        print(header_str)
        print("-" * len(header_str))

        for row in rows:
            row_str = ""
            for col in cols:
                val = row.get(col, "")
                if isinstance(val, float):
                    val_str = f"{val:.2f}"
                elif isinstance(val, int) and val > 1_000_000:
                    val_str = f"{val:,.0f}"
                else:
                    val_str = str(val)
                row_str += f"{val_str:<{col_widths[col]}}"
            print(row_str)

    if pc.unavailable_tickers:
        print(f"\nUnavailable Peer Tickers: {', '.join(pc.unavailable_tickers)}")


def print_news(data) -> None:
    """Print news analysis section."""
    if not data.news_analysis:
        return

    print_section("News Analysis")
    news = data.news_analysis
    print(f"News Period: {news.from_date} to {news.to_date}")
    if news.summary:
        print(f"\nSummary:\n{news.summary.summary}")
        if news.summary.material_events:
            print("\nMaterial Events:")
            for event in news.summary.material_events:
                print(f"  - {event}")
        if news.summary.limitations:
            print("\nLimitations / Notes:")
            for lim in news.summary.limitations:
                print(f"  - {lim}")
    print(f"\nArticles Analyzed: {len(news.articles)}")


def print_filings(data) -> None:
    """Print filing analysis section."""
    if data.filing_analysis:
        print_section("Filings Analysis")
        filing = data.filing_analysis
        print(f"Filing Path: {filing.filing_path}")
        print(f"Document Type: {filing.document_type}")
        print(f"Sections Found: {len(filing.sections)}")
        if filing.missing_sections:
            print(f"Missing Sections: {', '.join(filing.missing_sections)}")
        print(f"Summary: {filing.summary.summary}")

    if data.filing_comparison:
        print_section("Filings Comparison")
        comp = data.filing_comparison
        print(f"Previous: {comp.previous_filing_path}")
        print(f"Current:  {comp.current_filing_path}")
        if comp.major_changes:
            print("Major Changes:")
            for change in comp.major_changes:
                print(f"  - {change}")
        if comp.summary:
            print(f"Summary: {comp.summary.summary}")


def print_thesis(data) -> None:
    """Print final thesis report if generated."""
    if not data.investment_report:
        return

    report = data.investment_report
    print_section("Investment Thesis Report")
    print("Executive Summary:")
    print(report.executive_summary)
    print("\nBull Case:")
    print(report.bull_case)
    print("\nBear Case:")
    print(report.bear_case)
    print("\nKey Risks:")
    print(report.key_risks)
    print("\nPeer Positioning:")
    print(report.peer_positioning)
    print("\nInvestment Thesis:")
    print(report.investment_thesis)
    print("\nConclusion:")
    print(report.conclusion)


def main() -> None:
    """Execute CLI workflow."""
    configure_logging("financial-research-cli")
    args = parse_args()

    load_dotenv()
    google_key = os.getenv("GOOGLE_API_KEY")
    news_key = os.getenv("NEWS_API_KEY")

    if not google_key and not args.skip_thesis:
        print("WARNING: GOOGLE_API_KEY is not set in .env. Thesis and Gemini summarization may fail.")
    if not news_key and not args.no_news:
        print("WARNING: NEWS_API_KEY is not set in .env. News API retrieval may fail.")

    ticker = args.ticker.upper().strip()
    print(f"Starting Multi-Agent Research on Ticker: {ticker}...")

    include_filings = bool(args.filing_path)
    try:
        if args.use_adk:
            adk_result = run_adk_research(
                ticker=ticker,
                company_name=args.company_name,
                filing_path=args.filing_path,
                previous_filing_path=args.previous_filing_path,
                peer_tickers=args.peer_tickers,
                include_news=not args.no_news,
                include_filings=include_filings,
                include_peers=not args.no_peers,
                include_thesis=not args.skip_thesis,
                session_id=args.session_id,
            )
            response = adk_result.coordinator_response
            session_id = adk_result.session_id
        else:
            coordinator = CoordinatorAgent()
            response = coordinator.generate_report(
                ticker=ticker,
                company_name=args.company_name,
                filing_path=args.filing_path,
                previous_filing_path=args.previous_filing_path,
                peer_tickers=args.peer_tickers,
                include_news=not args.no_news,
                include_filings=include_filings,
                include_peers=not args.no_peers,
                include_thesis=not args.skip_thesis,
            )
            session_id = None
    except Exception as exc:
        print(f"Error during orchestration initialization: {exc}")
        sys.exit(1)

    print_execution_summary(response, session_id=session_id)
    data = response.consolidated_data
    print_financial(data)
    print_peers(data)
    print_news(data)
    print_filings(data)
    print_thesis(data)

    if args.save_output:
        payload = response.model_dump(mode="json")
        saved_path = persist_output_json(payload, ticker)
        print(f"\nSaved response JSON: {saved_path}")


if __name__ == "__main__":
    main()
