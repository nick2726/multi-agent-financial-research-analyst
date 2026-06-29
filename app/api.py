"""FastAPI service for production deployment (Docker/Cloud Run)."""

from __future__ import annotations

import os
from collections.abc import Sequence

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from adk.main import run_adk_research
from observability.logging_config import configure_logging
from observability.metrics import metrics

load_dotenv()
configure_logging("financial-research-api")

app = FastAPI(title="Multi-Agent Financial Research Analyst API", version="1.0.0")


class ResearchRequestApi(BaseModel):
    ticker: str
    company_name: str | None = None
    filing_path: str | None = None
    previous_filing_path: str | None = None
    peer_tickers: list[str] | None = None
    include_news: bool = True
    include_filings: bool = False
    include_peers: bool = True
    include_thesis: bool = True
    session_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="multi-agent-financial-research-analyst")


@app.get("/metrics")
def get_metrics() -> dict[str, object]:
    return metrics.snapshot()


@app.post("/v1/research")
def run_research(payload: ResearchRequestApi) -> dict[str, object]:
    metrics.increment("api.research_requests_total")
    try:
        with metrics.time("api.research_request_duration_ms"):
            result = run_adk_research(
                ticker=payload.ticker,
                company_name=payload.company_name,
                filing_path=payload.filing_path,
                previous_filing_path=payload.previous_filing_path,
                peer_tickers=cast_optional_sequence(payload.peer_tickers),
                include_news=payload.include_news,
                include_filings=payload.include_filings,
                include_peers=payload.include_peers,
                include_thesis=payload.include_thesis,
                session_id=payload.session_id,
            )
    except Exception as exc:
        metrics.increment("api.research_errors_total")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "session_id": result.session_id,
        "run_id": result.run_id,
        "response": result.coordinator_response.model_dump(mode="json"),
    }


def cast_optional_sequence(values: list[str] | None) -> Sequence[str] | None:
    if values is None:
        return None
    return list(values)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app.api:app", host="0.0.0.0", port=port, reload=False)
