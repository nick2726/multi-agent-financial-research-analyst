# Multi-Agent Financial Research Analyst

Placement-grade capstone project for building a production-minded financial research assistant with multi-agent orchestration, tool integration, evaluation, and cloud deployment.

## Project Goal

This project will evolve into a Multi-Agent Financial Research Analyst using Google Agent Development Kit, Gemini, FastAPI, Streamlit, yfinance, NewsAPI, filing parsers, pytest, Docker, and Google Cloud Run.

The implementation is intentionally incremental. Each milestone adds only the files and behavior needed for that stage so the architecture stays explainable in interviews.

## Milestone Roadmap

1. Environment setup
2. Financial Data Agent
3. News Agent
4. Filings Agent
5. Peer Comparison Agent
6. Coordinator Agent
7. Thesis Writer Agent
8. Google ADK integration
9. Session persistence
10. Evaluation framework
11. Dockerization
12. Cloud Run deployment
13. Observability

## Current Milestone

Milestone 1 sets up the Windows development environment:

- Python 3.11 virtual environment
- Git repository
- VS Code interpreter configuration
- Dependency manifest
- Secret-safe environment template

## Local Setup

From PowerShell:

```powershell
cd "D:\Projects\multi-agent-financial-research-analyst"
.\venv\Scripts\Activate.ps1
python --version
pip install -r requirements.txt
pytest
```

Expected Python version:

```text
Python 3.11.x
```

## Environment Variables

Create a local `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Then add your own API keys locally. Do not commit `.env`.

## Interview Notes

### How this milestone works

The project uses a local Python virtual environment to isolate dependencies from the system Python installation. Git tracks source files and configuration templates, while local secrets and the virtual environment stay untracked.

### Why this design was chosen

Python 3.11 is a stable production choice with broad library support. A simple `venv + pip` setup is easy to explain, easy to reproduce, and appropriate for a placement-focused portfolio project.

### Alternatives

- Conda: useful for data science stacks, but heavier than needed here.
- Poetry or uv: stronger dependency workflows, but unnecessary for the first milestone.
- Docker-first setup: valuable later, but premature before the application architecture exists.

### Limitations

- Dependency versions are not pinned yet.
- CI is not configured yet.
- No agents or application entrypoints are implemented in Milestone 1.

### Likely interview questions

**Why use a virtual environment?**  
To isolate project dependencies and avoid conflicts with system-wide packages.

**Why Python 3.11?**  
It balances modern language features with strong compatibility across AI, backend, and cloud libraries.

**Why keep secrets in `.env`?**  
It separates configuration from code and prevents accidental credential leaks in Git.

**Why not build all agents immediately?**  
Incremental implementation keeps the system easier to test, explain, and debug.
