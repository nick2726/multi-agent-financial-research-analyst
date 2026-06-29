# Multi-Agent Financial Research Analyst

Production-minded capstone project for equity-research automation using specialist agents and a fault-tolerant coordinator.

# Current Output Status

### INVESTMENT THESIS REPORT 

Executive Summary:
Infosys Limited was analyzed using the available financial, news, filings, and peer-comparison context. The strongest observable positives are Revenue growth is positive at 0.04570213207449292. and Operating profitability is visible with operating margin of 0.20928.. The main cautions are Valuation needs scrutiny because the reported P/E ratio is 13.621074..

Bull Case:
- Revenue growth is positive at 0.04570213207449292.
- Operating profitability is visible with operating margin of 0.20928.
- Return on equity is reported at 0.31439, indicating shareholder-return efficiency.

Bear Case:
- Valuation needs scrutiny because the reported P/E ratio is 13.621074.

Key Risks:
- Market-data and news APIs can be incomplete or delayed.
- The model uses supplied evidence only and does not replace analyst verification.
- Macroeconomic, currency, regulatory, and sector-cycle risks may affect the outcome.

Peer Positioning:
Target: INFY.NS
Peer universe: TCS.NS, WIPRO.NS, HCLTECH.NS, TECHM.NS, LTIMINDTREE.NS
Comparable companies with data: 5
Relative valuation should be interpreted with sector, scale, and profitability differences in mind.

Investment Thesis:
A constructive view is justified only if the company sustains growth, margins, and execution quality relative to peers. A neutral or cautious stance is more appropriate if valuation is demanding, key data is missing, or recent filings/news point to rising operational or regulatory risk.

Conclusion:
Overall, the thesis should be treated as research support rather than a buy/sell call. The next diligence step is to validate the agent output against the latest exchange filings, management commentary, and analyst consensus before making an investment decision.


## Architecture

```text
User Request
  |
  v
Coordinator Agent
  |
  +-- Financial Agent (fundamentals)
  +-- News Agent (news + summarization)
  +-- Filings Agent (filing analysis/comparison)
  +-- Peer Agent (benchmarking)
  |
  v
Thesis Writer Agent (final investment report)
```

## ADK Integration Strategy

The repository follows an incremental ADK migration pattern:

- Existing specialist agents remain unchanged.
- ADK wrappers in `adk/` expose those agents as reusable tools.
- ADK coordinator wrapper persists run history in local sessions.
- Migration is additive and does not break current custom orchestration.

### ADK Package Structure

```text
adk/
  agents/
    coordinator_agent.py
  sessions/
    session_store.py
  tools/
    specialist_tools.py
  main.py
```

## Quickstart

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Create local environment file and add secrets:

```powershell
Copy-Item .env.example .env
```

3. Run standard coordinator mode:

```powershell
python run_analyst.py INFY.NS --no-news
```

4. Run with filings:

```powershell
python run_analyst.py INFY.NS --filing-path data/filings/INFY_2025.pdf --previous-filing-path data/filings/INFY_2024.pdf
```

5. Run ADK wrapper mode:

```powershell
python run_analyst.py INFY.NS --use-adk --session-id demo-session-1
```

## CLI Options

- `ticker`: target ticker (default `MSFT`)
- `--company-name`: optional explicit company name
- `--filing-path`: current filing PDF path
- `--previous-filing-path`: previous filing PDF path
- `--peer-tickers`: explicit peer universe
- `--no-news`: skip News Agent
- `--no-peers`: skip Peer Agent
- `--skip-thesis`: skip Thesis Writer Agent
- `--use-adk`: run through ADK wrapper coordinator
- `--session-id`: ADK session identifier

## Testing

```powershell
pytest tests/test_coordinator_agent.py tests/test_peer_tools.py tests/test_adk_coordinator.py
```

## Design Principles

- Separation of concerns per agent
- Dependency injection for all specialist dependencies
- Structured outputs via Pydantic models
- Fault-tolerant coordinator execution
- Backward-compatible migration path toward full ADK runtime
