#!/usr/bin/env python3
"""CLI runner for Multi-Agent Financial Research Analyst."""

import argparse
import sys
import os
import json
from dotenv import load_dotenv

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.coordinator.coordinator_agent import CoordinatorAgent

def print_section(title: str):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Run Multi-Agent Financial Research Analyst.")
    parser.add_argument("ticker", type=str, nargs="?", default="MSFT", help="Ticker symbol to analyze (default: MSFT)")
    parser.add_argument("--no-news", action="store_true", help="Skip news analysis")
    parser.add_argument("--no-peers", action="store_true", help="Skip peer comparison")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Simple check for keys
    google_key = os.getenv("GOOGLE_API_KEY")
    news_key = os.getenv("NEWS_API_KEY")
    
    if not google_key:
        print("WARNING: GOOGLE_API_KEY is not set in .env. Gemini summarization will fail.")
    if not news_key:
        print("WARNING: NEWS_API_KEY is not set in .env. News API retrieval will fail.")

    ticker = args.ticker.upper().strip()
    print(f"Starting Multi-Agent Research on Ticker: {ticker}...")
    
    try:
        coordinator = CoordinatorAgent()
        response = coordinator.generate_report(
            ticker=ticker,
            include_news=not args.no_news,
            include_peers=not args.no_peers,
            include_filings=False  # Local filings PDF not provided for generic runner
        )
    except Exception as e:
        print(f"Error during orchestration initialization: {e}")
        sys.exit(1)

    # Output Results
    print_section("Execution Summary")
    print(f"Target Ticker:      {response.request.ticker}")
    print(f"Completed Agents:   {', '.join(response.completed_agents) if response.completed_agents else 'None'}")
    print(f"Failed Agents:      {', '.join(response.failed_agents) if response.failed_agents else 'None'}")
    
    if response.execution_metadata:
        print("\nDetails:")
        for meta in response.execution_metadata:
            status_symbol = "OK" if meta.status == "completed" else "FAIL"
            error_msg = f" - Error: {meta.error_type}: {meta.error_message}" if meta.error_message else ""
            print(f"  [{status_symbol}] {meta.agent_name} ({meta.duration_ms:.2f}ms){error_msg}")

    data = response.consolidated_data

    # 1. Financial Analysis
    if data.financial_analysis:
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
        print(f"  Operating Margin:  {metrics.operating_margins * 100:.2f}%" if metrics.operating_margins is not None else "  Operating Margin:  N/A")
        print(f"  Return on Equity:  {metrics.roe * 100:.2f}%" if metrics.roe is not None else "  Return on Equity:  N/A")
        print(f"  Revenue Growth:    {metrics.revenue_growth * 100:.2f}%" if metrics.revenue_growth is not None else "  Revenue Growth:    N/A")
        if data.financial_analysis.missing_fields:
            print(f"Missing Fields:      {', '.join(data.financial_analysis.missing_fields)}")

    # 2. Peer Comparison
    if data.peer_comparison:
        print_section("Peer Comparison")
        pc = data.peer_comparison
        print(f"Peers Compared: {', '.join(pc.peer_tickers)}")
        if pc.comparison_table and pc.comparison_table.rows:
            rows = pc.comparison_table.rows
            cols = pc.comparison_table.columns
            # Determine column widths
            col_widths = {}
            for col in cols:
                max_w = len(col)
                for r in rows:
                    val = str(r.get(col, ""))
                    if len(val) > max_w:
                        max_w = len(val)
                col_widths[col] = max_w + 2
            
            # Print header
            header_str = "".join(f"{col:<{col_widths[col]}}" for col in cols)
            print(header_str)
            print("-" * len(header_str))
            
            # Print rows
            for r in rows:
                row_str = ""
                for col in cols:
                    val = r.get(col, "")
                    if isinstance(val, float):
                        val_str = f"{val:.2f}"
                    elif isinstance(val, (int, float)) and val > 1_000_000:
                        val_str = f"{val:,.0f}"
                    else:
                        val_str = str(val)
                    row_str += f"{val_str:<{col_widths[col]}}"
                print(row_str)
        if pc.unavailable_tickers:
            print(f"\nUnavailable Peer Tickers: {', '.join(pc.unavailable_tickers)}")

    # 3. News Summary
    if data.news_analysis:
        print_section("News Analysis")
        news = data.news_analysis
        print(f"News Period: {news.from_date} to {news.to_date}")
        if news.summary:
            print(f"\nSummary:\n{news.summary.summary}")
            if news.summary.material_events:
                print("\nMaterial Events:")
                for event in news.summary.material_events:
                    print(f"  • {event}")
            if news.summary.limitations:
                print("\nLimitations / Notes:")
                for lim in news.summary.limitations:
                    print(f"  • {lim}")
        print(f"\nArticles Analyzed: {len(news.articles)}")
    if response.investment_report:
        report = response.investment_report

        print_section("Investment Research Report")

        print("\nExecutive Summary:")
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
if __name__ == "__main__":
    main()
