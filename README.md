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
## Docker Deployment

### Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

### Build the Docker Image

```bash
docker build -t multi-agent-financial-research-analyst .
```

### Run the Application

```bash
docker run -p 8080:8080 multi-agent-financial-research-analyst
```

The API will be available at:

- **API Base URL:** http://localhost:8080
- **Swagger Documentation:** http://localhost:8080/docs
- **OpenAPI Specification:** http://localhost:8080/openapi.json

### Run Using Docker Compose

Build and start the application:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d
```

Stop the application:

```bash
docker compose down
```

### Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Configure the required API keys inside `.env` if needed:

- GOOGLE_API_KEY
- GEMINI_API_KEY
- NEWS_API_KEY

### Verify Deployment

Open:

http://localhost:8080/docs

If the Swagger UI loads successfully, the deployment is working.
## Observability

The application includes lightweight observability features to monitor service health, API performance, and application behavior during execution.

### Logging

Structured logging is configured through the centralized logging module.

Features:
- Configurable log levels using `LOG_LEVEL`
- Configurable log format using `LOG_FORMAT`
- Human-readable text logs
- JSON formatted logs for machine-readable output
- Consistent service identification across CLI, API, and Streamlit applications

### Health Endpoint

The API exposes a health check endpoint for monitoring service availability.

```http
GET /healthz
```

Example Response:

```json
{
  "status": "ok",
  "service": "multi-agent-financial-research-analyst"
}
```

### Metrics Endpoint

The API exposes runtime metrics through:

```http
GET /metrics
```

The endpoint reports:

- Total research requests processed
- Total request execution time
- Average request latency
- Maximum request latency
- Minimum request latency

Example Response:

```json
{
  "counters": {
    "api.research_requests_total": 1
  },
  "timers": {
    "api.research_request_duration_ms": {
      "count": 1,
      "avg_ms": 6026.19,
      "max_ms": 6026.19,
      "min_ms": 6026.19
    }
  }
}
```

### Runtime Monitoring

The application records:

- API request lifecycle
- Agent execution logs
- Research request duration
- Application errors and exceptions
- Peer comparison execution
- Financial data retrieval events

### Verification

Observability can be verified using:

```bash
curl http://localhost:8080/healthz

curl http://localhost:8080/metrics
```

Or by opening:

- Health Check: `http://localhost:8080/healthz`
- Metrics: `http://localhost:8080/metrics`
- API Documentation: `http://localhost:8080/docs`


## Dashboard Screenshots

**1. News Analysis**
<img width="1490" height="820" alt="Screenshot 2026-07-01 022218" src="https://github.com/user-attachments/assets/6e64be00-d87d-46ac-b218-c9852f019047" />


**2. Peers Comparison**
<img width="1506" height="587" alt="Screenshot 2026-07-01 022146" src="https://github.com/user-attachments/assets/d53ba31d-6df6-4649-bbbc-660671855e12" />


**3. Financial Deep Dive**
<img width="1476" height="811" alt="Screenshot 2026-07-01 022123" src="https://github.com/user-attachments/assets/fb69d728-4220-470b-8b32-a638f810948b" />


**4. Company Overview & Metrics**
<img width="1516" height="860" alt="Screenshot 2026-07-01 021310" src="https://github.com/user-attachments/assets/0732e1c7-6f87-43d7-9089-338e36cda0b5" />
<img width="1465" height="785" alt="Screenshot 2026-07-01 021324" src="https://github.com/user-attachments/assets/aeec23bc-c525-4d4e-bf23-2352231a40db" />

