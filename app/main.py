"""FastAPI Application for SafeExec AI Trusted Control Plane."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import (
    RunCreate,
    RunResponse,
    ExecuteRequest,
    ExecuteResult,
    AgentRunRequest,
    AgentRunResponse,
)
from app.database import (
    init_db,
    record_run,
    fetch_all_runs,
    fetch_run_by_id,
)
from app.sandbox import sandbox_runner, generate_sandbox_name
from app.agent import agent_runner
from app.audit import audit_logger

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("safeexec.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and graceful shutdown."""
    logger.info("Initializing SafeExec AI Trusted Control Plane...")
    init_db()
    yield
    logger.info("SafeExec AI Trusted Control Plane shut down cleanly.")


app = FastAPI(
    title="SafeExec AI",
    description="Secure AI Agent Execution Platform utilizing isolated Celesto Cloud sandboxes.",
    version=settings.version,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder if present
static_dir = settings.base_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health", status_code=status.HTTP_200_OK)
def get_health() -> dict[str, str]:
    """Health check endpoint required by specification."""
    return {"status": "ok"}


@app.get("/api/runs", response_model=list[RunResponse], status_code=status.HTTP_200_OK)
def get_runs() -> list[RunResponse]:
    """Retrieve all stored run records from the ledger."""
    return fetch_all_runs()


@app.post("/api/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def post_run(run: RunCreate) -> RunResponse:
    """Record a run in the database ledger.
    
    Rejects 'host' as execution target with HTTP 400.
    """
    if run.execution_target != "celesto_sandbox":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="execution_target must equal 'celesto_sandbox'. Host execution is prohibited."
        )
    return record_run(run)


@app.get("/api/runs/{run_id}", response_model=RunResponse, status_code=status.HTTP_200_OK)
def get_single_run(run_id: str) -> RunResponse:
    """Retrieve details for a single run by ID."""
    record = fetch_run_by_id(run_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")
    return record


@app.post("/api/execute", response_model=ExecuteResult, status_code=status.HTTP_200_OK)
def execute_code(request: ExecuteRequest) -> ExecuteResult:
    """Execute code strictly inside an isolated Celesto sandbox."""
    sbx_name = request.sandbox_name or generate_sandbox_name()
    return sandbox_runner.execute(
        code=request.code,
        language=request.language,
        timeout_s=request.timeout_s,
        sandbox_name=sbx_name,
        persistent=request.persistent
    )


@app.post("/api/agent/run", response_model=AgentRunResponse, status_code=status.HTTP_200_OK)
def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Accept natural-language task and execute code exclusively via Celesto sandbox tool calling."""
    return agent_runner.run(request)


@app.get("/api/reports", status_code=status.HTTP_200_OK)
def get_reports() -> dict[str, Any]:
    """Retrieve all verification and evaluation reports."""
    reports_dir = settings.reports_dir
    report_files = [
        "problem.json",
        "capabilities.json",
        "lifecycle.json",
        "reliability.json",
        "containment.json",
        "failure_policy.json",
        "concurrency.json"
    ]
    results: dict[str, Any] = {}

    for rf in report_files:
        path = reports_dir / rf
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    results[rf.replace(".json", "")] = json.load(f)
            except Exception as e:
                results[rf.replace(".json", "")] = {"error": f"Failed to parse {rf}: {e}"}
        else:
            results[rf.replace(".json", "")] = None

    postmortem_path = reports_dir / "postmortem.md"
    if postmortem_path.exists():
        with open(postmortem_path, "r", encoding="utf-8") as f:
            results["postmortem"] = f.read()
    else:
        results["postmortem"] = None

    return results


@app.get("/api/audit/logs", status_code=status.HTTP_200_OK)
def get_audit_logs(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve recent security and command audit log events."""
    return audit_logger.read_recent_events(limit=limit)


@app.get("/", response_class=HTMLResponse)
def index_dashboard():
    """Simple HTML operator dashboard for live monitoring and testing."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SafeExec AI - Control Plane Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
    .container { max-width: 1100px; margin: 0 auto; }
    h1 { color: #38bdf8; margin-bottom: 4px; }
    p.sub { color: #94a3b8; margin-top: 0; margin-bottom: 24px; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; background: #0369a1; color: #e0f2fe; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 18px; }
    .card h3 { margin-top: 0; color: #7dd3fc; border-bottom: 1px solid #334155; padding-bottom: 8px; }
    textarea, input { width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: #f8fafc; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 0.9rem; margin-bottom: 10px; }
    button { background: #0284c7; color: white; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    button:hover { background: #0369a1; }
    pre { background: #0b1120; border: 1px solid #334155; padding: 12px; border-radius: 6px; overflow-x: auto; color: #a5f3fc; font-size: 0.85rem; max-height: 250px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; }
  </style>
</head>
<body>
  <div class="container">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1>SafeExec AI</h1>
        <p class="sub">Secure AI Agent Execution Platform &middot; Celesto Cloud Sandbox Ledger</p>
      </div>
      <span class="badge">Isolated MicroVM Execution</span>
    </div>

    <div class="grid">
      <div class="card">
        <h3>AI Agent Coding Task</h3>
        <textarea id="taskInput" rows="3" placeholder="Enter coding task (e.g. Calculate the first 10 Fibonacci numbers)...">Calculate the first 10 Fibonacci numbers using recursion</textarea>
        <button onclick="runAgentTask()">Dispatch to Agent</button>
        <div id="agentStatus" style="margin-top: 8px; color: #94a3b8;"></div>
        <pre id="agentOutput">Agent outputs will display here...</pre>
      </div>

      <div class="card">
        <h3>Direct Sandbox Code Execution</h3>
        <textarea id="codeInput" rows="3" placeholder="print('Hello from Celesto Sandbox')">print("SafeExec guest code running inside isolated Celesto microVM")</textarea>
        <button onclick="runSandboxCode()">Run in Sandbox</button>
        <pre id="codeOutput">Sandbox execution telemetry will display here...</pre>
      </div>
    </div>

    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="margin: 0; border: none;">PostgreSQL Execution Ledger (GET /api/runs)</h3>
        <button onclick="loadRuns()" style="padding: 6px 12px; font-size: 0.8rem;">Refresh Ledger</button>
      </div>
      <table id="runsTable">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Sandbox Name</th>
            <th>Problem ID</th>
            <th>Target</th>
            <th>State</th>
            <th>Success</th>
            <th>Time (s)</th>
          </tr>
        </thead>
        <tbody id="runsBody">
          <tr><td colspan="7">Loading ledger records...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <script>
    async function loadRuns() {
      try {
        const res = await fetch('/api/runs');
        const runs = await res.json();
        const tbody = document.getElementById('runsBody');
        tbody.innerHTML = '';
        runs.forEach(r => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td><code>${r.run_id}</code></td>
            <td><code>${r.sandbox_name}</code></td>
            <td>${r.problem_id}</td>
            <td><span style="color: #38bdf8">${r.execution_target}</span></td>
            <td><span style="color: ${r.state === 'succeeded' ? '#4ade80' : '#f87171'}">${r.state}</span></td>
            <td>${r.success !== null ? (r.success ? '&#10003; True' : '&#10007; False') : '-'}</td>
            <td>${r.execution_time ? r.execution_time.toFixed(3) : '-'}</td>
          `;
          tbody.appendChild(row);
        });
      } catch (err) {
        console.error(err);
      }
    }

    async function runAgentTask() {
      const task = document.getElementById('taskInput').value;
      const statusDiv = document.getElementById('agentStatus');
      const outPre = document.getElementById('agentOutput');
      statusDiv.innerText = 'Dispatching to agent & Celesto sandbox...';
      try {
        const res = await fetch('/api/agent/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ task })
        });
        const data = await res.json();
        statusDiv.innerText = `Finished in ${data.total_wall_clock_s.toFixed(2)}s`;
        outPre.innerText = JSON.stringify(data, null, 2);
        loadRuns();
      } catch (err) {
        statusDiv.innerText = 'Failed: ' + err;
      }
    }

    async function runSandboxCode() {
      const code = document.getElementById('codeInput').value;
      const outPre = document.getElementById('codeOutput');
      outPre.innerText = 'Executing in Celesto sandbox...';
      try {
        const res = await fetch('/api/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ code })
        });
        const data = await res.json();
        outPre.innerText = JSON.stringify(data, null, 2);
        loadRuns();
      } catch (err) {
        outPre.innerText = 'Error: ' + err;
      }
    }

    window.onload = loadRuns;
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

