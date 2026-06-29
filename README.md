# Multi-Agent Financial Research Analyst

Production-minded capstone project for equity-research automation using specialist agents and a fault-tolerant coordinator.

## Current Milestone Status

- Milestone 1: Environment setup - complete
- Milestone 2: Financial Agent - complete
- Milestone 3: News Agent - complete
- Milestone 4: Filings Agent - implemented and ready for coordinator validation
- Milestone 5: Peer Comparison Agent - complete
- Milestone 6: Coordinator Agent - complete with partial-failure isolation
- Milestone 7: Thesis Writer Agent - complete and integrated into coordinator
- Milestone 8: ADK integration - started with wrapper architecture and session persistence

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
