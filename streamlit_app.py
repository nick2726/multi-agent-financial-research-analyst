"""Streamlit local demo for the Multi-Agent Financial Research Analyst."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from adk.main import run_adk_research
from observability.logging_config import configure_logging

load_dotenv()
configure_logging("financial-research-streamlit")

st.set_page_config(
    page_title="Multi-Agent Financial Research Analyst",
    page_icon="chart",
    layout="wide",
)

st.title("Multi-Agent Financial Research Analyst")
st.caption("Coordinator + Financial Data + News + Filings + Peers + Thesis Writer, built for a judge-facing local demo.")

with st.sidebar:
    st.header("Research Setup")
    ticker = st.text_input("Ticker", value="INFY.NS", help="Examples: INFY.NS, TCS.NS, MSFT, AAPL")
    company_name = st.text_input("Company name override", value="")
    peer_text = st.text_input("Peer tickers", value="", help="Optional comma-separated list. Leave blank for automatic peers.")
    include_news = st.toggle("News Agent", value=True)
    include_peers = st.toggle("Peer Comparison Agent", value=True)
    include_thesis = st.toggle("Thesis Writer Agent", value=True)
    include_filings = st.toggle("Filings Agent", value=False)
    filing_path = st.text_input("Current filing PDF path", value="", disabled=not include_filings)
    previous_filing_path = st.text_input("Previous filing PDF path", value="", disabled=not include_filings)
    session_id = st.text_input("Session ID", value="demo-session")
    run_button = st.button("Run Research", type="primary", use_container_width=True)

with st.expander("API readiness", expanded=False):
    st.write(
        {
            "NEWS_API_KEY": "configured" if os.getenv("NEWS_API_KEY") else "fallback RSS will be used",
            "GOOGLE_API_KEY/GEMINI_API_KEY": "configured" if (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")) else "local summaries/thesis fallback will be used",
        }
    )

if run_button:
    peer_tickers = [item.strip().upper() for item in peer_text.split(",") if item.strip()] or None
    with st.spinner("Specialist agents are collecting and synthesizing research..."):
        result = run_adk_research(
            ticker=ticker,
            company_name=company_name.strip() or None,
            filing_path=filing_path.strip() or None,
            previous_filing_path=previous_filing_path.strip() or None,
            peer_tickers=peer_tickers,
            include_news=include_news,
            include_filings=include_filings and bool(filing_path.strip()),
            include_peers=include_peers,
            include_thesis=include_thesis,
            session_id=session_id.strip() or None,
        )

    response = result.coordinator_response
    data = response.consolidated_data

    top_cols = st.columns(4)
    top_cols[0].metric("Session", result.session_id)
    top_cols[1].metric("Completed", len(response.completed_agents))
    top_cols[2].metric("Failed", len(response.failed_agents))
    top_cols[3].metric("Ticker", response.request.ticker)

    if response.failed_agents:
        st.warning("Some agents failed gracefully: " + ", ".join(response.failed_agents))

    tabs = st.tabs(["Investment Thesis", "Financials", "Peers", "News", "Filings", "Execution JSON"])

    with tabs[0]:
        report = data.investment_report
        if report:
            st.caption(f"Report source: {report.source}")
            st.subheader("Executive Summary")
            st.write(report.executive_summary)
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Bull Case")
                st.write(report.bull_case)
                st.subheader("Peer Positioning")
                st.write(report.peer_positioning)
            with col_b:
                st.subheader("Bear Case")
                st.write(report.bear_case)
                st.subheader("Key Risks")
                st.write(report.key_risks)
            st.subheader("Investment Thesis")
            st.write(report.investment_thesis)
            st.subheader("Conclusion")
            st.write(report.conclusion)
        else:
            st.info("Thesis Writer Agent was skipped or unavailable.")

    with tabs[1]:
        analysis = data.financial_analysis
        if analysis:
            st.subheader(analysis.company.name)
            st.write(
                {
                    "ticker": analysis.company.ticker,
                    "sector": analysis.company.sector,
                    "industry": analysis.company.industry,
                    "exchange": analysis.company.exchange,
                    "currency": analysis.company.currency,
                }
            )
            metrics = analysis.metrics.model_dump()
            st.dataframe(pd.DataFrame([metrics]).T.rename(columns={0: "value"}), use_container_width=True)
            if analysis.missing_fields:
                st.caption("Missing fields: " + ", ".join(analysis.missing_fields))
        else:
            st.info("Financial Data Agent did not return data.")

    with tabs[2]:
        peers = data.peer_comparison
        if peers and peers.comparison_table.rows:
            st.caption("Peer universe: " + ", ".join(peers.peer_tickers))
            st.dataframe(pd.DataFrame(peers.comparison_table.rows), use_container_width=True)
            if peers.unavailable_tickers:
                st.caption("Unavailable tickers: " + ", ".join(peers.unavailable_tickers))
        else:
            st.info("Peer Comparison Agent was skipped or unavailable.")

    with tabs[3]:
        news = data.news_analysis
        if news:
            st.subheader("News Summary")
            st.write(news.summary.summary)
            if news.summary.material_events:
                st.subheader("Material Events")
                for event in news.summary.material_events:
                    st.write(f"- {event}")
            st.subheader("Articles")
            for article in news.articles:
                st.markdown(f"[{article.title}]({article.url})")
                st.caption(f"{article.source} | {article.publication_date.date().isoformat()}")
            if news.summary.limitations:
                st.caption("Limitations: " + "; ".join(news.summary.limitations))
        else:
            st.info("News Agent was skipped or unavailable.")

    with tabs[4]:
        filing = data.filing_analysis
        comparison = data.filing_comparison
        if filing:
            st.subheader("Filing Summary")
            st.write(filing.summary.summary)
            if filing.summary.key_points:
                for point in filing.summary.key_points:
                    st.write(f"- {point}")
            st.caption(f"Sections found: {len(filing.sections)}")
        if comparison:
            st.subheader("Year-over-Year Changes")
            for change in comparison.major_changes:
                st.write(f"- {change}")
        if not filing and not comparison:
            st.info("Filings Agent was skipped or no PDF path was supplied.")

    with tabs[5]:
        st.json(response.model_dump(mode="json"))
else:
    st.info("Enter a ticker and run the workflow. For a strong local demo, try INFY.NS or TCS.NS with News, Peers, and Thesis enabled.")
