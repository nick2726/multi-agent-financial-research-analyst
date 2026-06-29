$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host ".venv not found. Create it first: py -3.11 -m venv .venv"
    exit 1
}

& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install fastapi uvicorn

$env:PORT = "8080"
& .\.venv\Scripts\python.exe -m uvicorn app.api:app --host 0.0.0.0 --port 8080
