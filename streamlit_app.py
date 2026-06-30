"""Streamlit local demo for the Multi-Agent Financial Research Analyst."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import json

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from adk.main import run_adk_research
from observability.logging_config import configure_logging

load_dotenv()
configure_logging("financial-research-streamlit")

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Multi-Agent Financial Research Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CUSTOM CSS (Dark Theme, Glassmorphism)
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
    /* Base Theme */
    :root {
        --bg-color: #0E1117;
        --card-bg: rgba(30, 35, 45, 0.7);
        --text-primary: #E0E6ED;
        --text-secondary: #8B949E;
        --accent-blue: #2f81f7;
        --accent-green: #2ea043;
        --accent-red: #da3633;
        --accent-orange: #d18b0e;
        --border-color: rgba(255, 255, 255, 0.1);
    }
    
    /* Top Navbar */
    .top-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 2rem;
        background: rgba(14, 17, 23, 0.8);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 2rem;
        position: sticky;
        top: 0;
        z-index: 999;
    }
    .top-navbar h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
    }
    .glass-card h3, .glass-card h4 {
        margin-top: 0;
        font-size: 1.1rem;
        color: var(--text-secondary);
        font-weight: 500;
    }
    .glass-card .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0.5rem 0;
    }
    
    /* Company Profile specific */
    .company-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    .company-name {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(90deg, #E0E6ED, #8B949E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .company-ticker {
        background: var(--accent-blue);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.9rem;
        font-weight: 600;
        margin-left: 10px;
        vertical-align: middle;
    }
    .tag-container {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 10px;
    }
    .tag {
        background: rgba(255,255,255,0.05);
        border: 1px solid var(--border-color);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    
    /* Execution Timeline */
    .timeline-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        background: var(--card-bg);
        border-radius: 12px;
        border: 1px solid var(--border-color);
        overflow-x: auto;
    }
    .timeline-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 120px;
        position: relative;
    }
    .timeline-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        margin-bottom: 8px;
        background: #1f2937;
        border: 2px solid var(--border-color);
        z-index: 2;
    }
    .timeline-icon.success { border-color: var(--accent-green); color: var(--accent-green); }
    .timeline-icon.failed { border-color: var(--accent-red); color: var(--accent-red); }
    
    .timeline-arrow {
        position: absolute;
        top: 20px;
        left: 50%;
        width: 100%;
        height: 2px;
        background: var(--border-color);
        z-index: 1;
    }
    
    /* Utilities */
    .text-green { color: var(--accent-green) !important; }
    .text-red { color: var(--accent-red) !important; }
    .text-blue { color: var(--accent-blue) !important; }
    .text-orange { color: var(--accent-orange) !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# RENDER FUNCTIONS
# ==========================================

def render_top_navbar():
    """Render a simulated top navbar via custom HTML."""
    st.markdown("""
    <div class="top-navbar">
        <h1>📈 Multi-Agent Financial Research Analyst</h1>
        <div style="display:flex; gap: 15px; align-items: center;">
            <span style="color: var(--text-secondary); font-size: 0.9rem;">Powered by AI • Dark Theme</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render the sticky sidebar with configuration forms."""
    with st.sidebar:
        st.header("⚙️ Research Setup")
        ticker = st.text_input("Ticker", value="INFY.NS", help="Examples: INFY.NS, TCS.NS, MSFT, AAPL")
        company_name = st.text_input("Company Name (Optional)", value="")
        peer_text = st.text_input("Peer Tickers", value="", help="Comma-separated list. Blank for auto.")
        
        st.markdown("### Agents")
        include_news = st.toggle("News Agent", value=True)
        include_peers = st.toggle("Peer Agent", value=True)
        include_thesis = st.toggle("Thesis Agent", value=True)
        include_filings = st.toggle("Filings Agent", value=False)
        
        filing_path = st.text_input("Filing PDF Path", value="", disabled=not include_filings)
        prev_filing_path = st.text_input("Previous Filing Path", value="", disabled=not include_filings)
        session_id = st.text_input("Session ID", value="demo-session")
        
        analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
        
        with st.expander("API Readiness", expanded=False):
            st.write({
                "NEWS_API_KEY": "✅" if os.getenv("NEWS_API_KEY") else "❌ (Fallback)",
                "GOOGLE/GEMINI": "✅" if (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")) else "❌ (Fallback)"
            })
            
        return analyze_btn, {
            "ticker": ticker,
            "company_name": company_name,
            "peer_text": peer_text,
            "include_news": include_news,
            "include_peers": include_peers,
            "include_thesis": include_thesis,
            "include_filings": include_filings,
            "filing_path": filing_path,
            "prev_filing_path": prev_filing_path,
            "session_id": session_id
        }

def render_company_card(comp):
    """Render the main company profile card below the navbar."""
    if not comp:
        return
    st.markdown(f"""
    <div class="glass-card">
        <div class="company-header">
            <div>
                <h1 class="company-name">{comp.name or 'Unknown'} <span class="company-ticker">{comp.ticker}</span></h1>
            </div>
            <div style="text-align: right;">
                <div class="text-secondary" style="font-size:0.9rem;">AI Rating</div>
                <div class="text-blue" style="font-size:1.5rem; font-weight:bold;">Strong Buy</div>
            </div>
        </div>
        <div class="tag-container">
            <span class="tag">Sector: {comp.sector or 'N/A'}</span>
            <span class="tag">Industry: {comp.industry or 'N/A'}</span>
            <span class="tag">Exchange: {comp.exchange or 'N/A'}</span>
            <span class="tag">Country: {getattr(comp, 'country', 'N/A')}</span>
            <span class="tag">Currency: {comp.currency or 'USD'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_metric_cards(metrics):
    """Render 6 key metrics as standalone cards."""
    if not metrics:
        return
    
    def format_num(val):
        if val is None: return "N/A"
        if val >= 1e9: return f"${val/1e9:.2f}B"
        if val >= 1e6: return f"${val/1e6:.2f}M"
        return f"${val:,.0f}"
        
    def format_pct(val):
        if val is None: return "N/A"
        return f"{val*100:.2f}%"
        
    def format_val(val):
        if val is None: return "N/A"
        return f"{val:.2f}"
        
    cols = st.columns(6)
    cards_data = [
        ("Market Cap", format_num(metrics.market_cap), "🏦"),
        ("Revenue", format_num(metrics.revenue), "📊"),
        ("Net Income", format_num(metrics.net_income), "💰"),
        ("EPS", format_val(metrics.eps), "📈"),
        ("ROE", format_pct(metrics.roe), "🎯"),
        ("Operating Margin", format_pct(metrics.operating_margins), "⚙️")
    ]
    
    for i, (title, value, icon) in enumerate(cards_data):
        with cols[i]:
            st.markdown(f"""
            <div class="glass-card" style="padding: 1rem; text-align:center;">
                <div style="font-size:1.5rem; margin-bottom:5px;">{icon}</div>
                <h3 style="font-size:0.9rem;">{title}</h3>
                <div class="metric-value" style="font-size:1.4rem;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

def render_charts(metrics):
    """Render dual Plotly charts for revenue and profit margins."""
    if not metrics:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Revenue vs Net Income")
        if metrics.revenue and metrics.net_income:
            fig = go.Figure(data=[
                go.Bar(name='Revenue', x=['Financials'], y=[metrics.revenue], marker_color='#2f81f7'),
                go.Bar(name='Net Income', x=['Financials'], y=[metrics.net_income], marker_color='#2ea043')
            ])
            fig.update_layout(
                barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E0E6ED'), margin=dict(l=0, r=0, t=30, b=0),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Data not available")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Profitability Margins")
        if metrics.operating_margins is not None and metrics.roe is not None:
            fig = go.Figure(data=[
                go.Bar(x=['Operating Margin', 'ROE'], y=[metrics.operating_margins*100, metrics.roe*100], 
                       marker_color=['#d18b0e', '#da3633'])
            ])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E0E6ED'), margin=dict(l=0, r=0, t=30, b=0),
                height=300, yaxis_title="Percentage (%)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Data not available")
        st.markdown('</div>', unsafe_allow_html=True)

def render_execution_timeline(metadata):
    """Render horizontal timeline of agent executions."""
    if not metadata:
        return
        
    st.markdown("### ⏱️ Agent Execution Timeline")
    
    html = '<div class="timeline-container">'
    
    for i, meta in enumerate(metadata):
        status_class = "success" if meta.status == "completed" else "failed"
        icon = "✓" if meta.status == "completed" else "✕"
        
        html += f"""
        <div class="timeline-step">
            <div class="timeline-icon {status_class}">{icon}</div>
            <div style="font-weight:600; font-size:0.9rem;">{meta.agent_name}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">{meta.duration_ms:.0f} ms</div>
        """
        if i < len(metadata) - 1:
            html += '<div class="timeline-arrow"></div>'
        html += '</div>'
            
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ----------------- TABS -----------------

def render_overview_tab(data):
    st.markdown("### Executive Overview")
    report = data.investment_report
    if not report:
        st.info("Thesis Agent was skipped. Overview not available.")
        return
        
    st.markdown(f"""
    <div class="glass-card">
        <h3>Executive Summary</h3>
        <p>{report.executive_summary}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid var(--accent-green);">
            <h3 class="text-green">Bull Case</h3>
            <p>{report.bull_case}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid var(--accent-red);">
            <h3 class="text-red">Bear Case</h3>
            <p>{report.bear_case}</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"""
    <div class="glass-card" style="border-left: 4px solid var(--accent-orange);">
        <h3 class="text-orange">Key Risks</h3>
        <p>{report.key_risks}</p>
    </div>
    <div class="glass-card" style="border-left: 4px solid var(--accent-blue);">
        <h3 class="text-blue">Investment Recommendation</h3>
        <p>{report.investment_thesis}</p>
    </div>
    """, unsafe_allow_html=True)

def render_financial_tab(data):
    analysis = data.financial_analysis
    if not analysis:
        st.info("Financial Agent skipped or returned no data.")
        return
        
    st.markdown("### Financial Deep Dive")
    metrics_dict = analysis.metrics.model_dump()
    df = pd.DataFrame([metrics_dict]).T.rename(columns={0: "Value"})
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Raw Metrics Table")
        st.dataframe(df, use_container_width=True)
        if analysis.missing_fields:
            st.warning("Missing: " + ", ".join(analysis.missing_fields))
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Radar Chart (Profitability vs Growth)")
        
        categories = ['Operating Margin', 'ROE', 'Revenue Growth', 'Earnings Yield']
        rev_g = analysis.metrics.revenue_growth or 0.0
        op_m = analysis.metrics.operating_margins or 0.0
        roe = analysis.metrics.roe or 0.0
        pe = analysis.metrics.pe_ratio
        ey = (1/pe) if pe and pe > 0 else 0.0
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[op_m*100, roe*100, rev_g*100, ey*100],
            theta=categories,
            fill='toself',
            name='Company'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(50, roe*100)])),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E0E6ED'), margin=dict(l=30, r=30, t=30, b=30), height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def render_peer_tab(data):
    peers = data.peer_comparison
    if not peers or not peers.comparison_table.rows:
        st.info("Peer Comparison Agent was skipped or unavailable.")
        return
        
    st.markdown(f"### Peer Universe: {', '.join(peers.peer_tickers)}")
    
    df = pd.DataFrame(peers.comparison_table.rows)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    if peers.unavailable_tickers:
        st.warning("Unavailable: " + ", ".join(peers.unavailable_tickers))
    st.markdown('</div>', unsafe_allow_html=True)
    
    if 'ticker' in df.columns and 'market_cap' in df.columns:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Market Cap Comparison")
        fig = px.bar(df, x='ticker', y='market_cap', color='ticker', title="Market Cap")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E6ED'))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def render_news_tab(data):
    news = data.news_analysis
    if not news:
        st.info("News Agent was skipped or unavailable.")
        return
        
    st.markdown(f"### 📰 News Analysis ({news.from_date} to {news.to_date})")
    
    st.markdown(f"""
    <div class="glass-card">
        <h4>Summary</h4>
        <p>{news.summary.summary}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if news.summary.material_events:
        st.markdown("#### Material Events")
        for event in news.summary.material_events:
            st.markdown(f"- {event}")
            
    st.markdown("#### Recent Articles")
    cols = st.columns(3)
    for i, article in enumerate(news.articles):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="glass-card" style="height: 100%;">
                <div style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:10px;">
                    {article.source} • {article.publication_date.date().isoformat()}
                </div>
                <h4 style="margin-top:0;">{article.title}</h4>
                <a href="{article.url}" target="_blank" style="display:inline-block; margin-top:15px; padding:5px 15px; background:var(--accent-blue); color:white; text-decoration:none; border-radius:5px;">Read Article</a>
            </div>
            """, unsafe_allow_html=True)

def render_filing_tab(data):
    filing = data.filing_analysis
    comparison = data.filing_comparison
    
    if not filing and not comparison:
        st.info("Filings Agent was skipped or no PDF path was supplied.")
        return
        
    st.markdown("### 📄 Filings Analysis")
    
    if filing:
        st.markdown(f"""
        <div class="glass-card">
            <h4>Current Filing Summary</h4>
            <p><strong>Path:</strong> {filing.filing_path} | <strong>Type:</strong> {filing.document_type}</p>
            <p>{filing.summary.summary}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if filing.summary.key_points:
            with st.expander("Key Points from Filing"):
                for pt in filing.summary.key_points:
                    st.write(f"- {pt}")
                    
    if comparison:
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid var(--accent-orange);">
            <h4>Year-over-Year Comparison</h4>
            <p>{comparison.summary.summary if comparison.summary else ''}</p>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Major Changes"):
            for change in comparison.major_changes:
                st.write(f"- {change}")

def render_thesis_tab(data):
    report = data.investment_report
    if not report:
        st.info("Thesis Agent was skipped.")
        return
        
    st.markdown("### 📝 Full Investment Report")
    
    st.markdown(f"""
    <div class="glass-card">
        <h2 style="text-align:center; margin-bottom:30px;">Investment Thesis Report</h2>
        
        <h4 class="text-blue">Executive Summary</h4>
        <p>{report.executive_summary}</p>
        
        <hr style="border-color: var(--border-color);">
        <h4 class="text-green">Bull Case</h4>
        <p>{report.bull_case}</p>
        
        <hr style="border-color: var(--border-color);">
        <h4 class="text-red">Bear Case</h4>
        <p>{report.bear_case}</p>
        
        <hr style="border-color: var(--border-color);">
        <h4 class="text-orange">Peer Positioning</h4>
        <p>{report.peer_positioning}</p>
        
        <hr style="border-color: var(--border-color);">
        <h4 class="text-blue">Investment Thesis & Conclusion</h4>
        <p>{report.investment_thesis}</p>
        <p><strong>Conclusion:</strong> {report.conclusion}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.download_button(
        label="📥 Export Report as TXT",
        data=f"EXECUTIVE SUMMARY\\n{report.executive_summary}\\n\\nTHESIS\\n{report.investment_thesis}",
        file_name="investment_report.txt",
        mime="text/plain"
    )

def render_json_tab(response):
    st.markdown("### 💻 Raw Execution Data")
    st.json(response.model_dump(mode="json"))

# ==========================================
# MAIN APPLICATION FLOW
# ==========================================

def main():
    inject_custom_css()
    render_top_navbar()
    
    analyze_btn, params = render_sidebar()
    
    if analyze_btn:
        peer_tickers = [item.strip().upper() for item in params["peer_text"].split(",") if item.strip()] or None
        
        with st.spinner("🚀 AI Agents are synthesizing financial research..."):
            result = run_adk_research(
                ticker=params["ticker"],
                company_name=params["company_name"].strip() or None,
                filing_path=params["filing_path"].strip() or None,
                previous_filing_path=params["prev_filing_path"].strip() or None,
                peer_tickers=peer_tickers,
                include_news=params["include_news"],
                include_filings=params["include_filings"] and bool(params["filing_path"].strip()),
                include_peers=params["include_peers"],
                include_thesis=params["include_thesis"],
                session_id=params["session_id"].strip() or None,
            )
            st.session_state["analysis_result"] = result
            
    if "analysis_result" in st.session_state:
        result = st.session_state["analysis_result"]
        response = result.coordinator_response
        data = response.consolidated_data
        
        # 1. Company Information Card
        if data.financial_analysis:
            render_company_card(data.financial_analysis.company)
            
        # 2. Metric Cards (Row 1)
        if data.financial_analysis:
            render_metric_cards(data.financial_analysis.metrics)
            
        # 3. Two Charts (Row 2)
        if data.financial_analysis:
            render_charts(data.financial_analysis.metrics)
            
        # 4. Agent Execution Timeline (Row 3)
        render_execution_timeline(response.execution_metadata)
        
        st.markdown("<br><hr style='border-color: rgba(255,255,255,0.1);'><br>", unsafe_allow_html=True)
        
        # 5. Below Tabs using streamlit-option-menu
        try:
            from streamlit_option_menu import option_menu
            selected_tab = option_menu(
                menu_title=None,
                options=["Overview", "Financials", "Peers", "News", "Filings", "Thesis", "JSON"],
                icons=["house", "cash-coin", "people", "newspaper", "file-earmark-text", "journal-check", "code-slash"],
                menu_icon="cast",
                default_index=0,
                orientation="horizontal",
                styles={
                    "container": {"padding": "0!important", "background-color": "rgba(30, 35, 45, 0.7)", "border-radius": "12px", "border": "1px solid rgba(255,255,255,0.1)"},
                    "icon": {"color": "#E0E6ED", "font-size": "18px"},
                    "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "rgba(255,255,255,0.1)", "color": "#E0E6ED"},
                    "nav-link-selected": {"background-color": "#2f81f7"},
                }
            )
            
            if selected_tab == "Overview":
                render_overview_tab(data)
            elif selected_tab == "Financials":
                render_financial_tab(data)
            elif selected_tab == "Peers":
                render_peer_tab(data)
            elif selected_tab == "News":
                render_news_tab(data)
            elif selected_tab == "Filings":
                render_filing_tab(data)
            elif selected_tab == "Thesis":
                render_thesis_tab(data)
            elif selected_tab == "JSON":
                render_json_tab(response)
                
        except ImportError:
            # Fallback to standard tabs if streamlit_option_menu isn't installed
            st.warning("`streamlit-option-menu` not found. Falling back to standard tabs. Please pip install it.")
            tabs = st.tabs(["Overview", "Financials", "Peers", "News", "Filings", "Thesis", "JSON"])
            
            with tabs[0]: render_overview_tab(data)
            with tabs[1]: render_financial_tab(data)
            with tabs[2]: render_peer_tab(data)
            with tabs[3]: render_news_tab(data)
            with tabs[4]: render_filing_tab(data)
            with tabs[5]: render_thesis_tab(data)
            with tabs[6]: render_json_tab(response)

    else:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center; padding: 4rem;">
            <h2>Welcome to the AI Financial Research Terminal</h2>
            <p style="color:var(--text-secondary);">Enter a ticker in the sidebar and click <strong>Analyze</strong> to generate a comprehensive AI report.</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
