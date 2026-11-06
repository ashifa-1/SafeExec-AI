# SafeExec AI - Development Status & Verification Ledger

**Last Updated:** 2026-11-06 (Automated Build & Evaluation Cycle)

---

## 1. Completed Functionality

### Core Celesto Integration
- [x] Official Celesto Python SDK (`celesto 0.1.13`) inspected and integrated.
- [x] Windows compatibility resolution via short-path venv (`D:\sv`), bypassing 260 MAX_PATH limitation, and platform stubs for Linux-only modules (`celesto_core`, `pwd`).
- [x] Verified Celesto native classes: `celesto.sdk.CloudComputer`, `celesto.callbacks.Callback`, `celesto.callbacks.CommandBlockedError`, `celesto.types.InternetSettings`.
- [x] Celesto Capability 1 (Persistence): Demonstrates stopping and resuming sandboxes while preserving workspace file state (`/workspace/persistent_data.txt`).
- [x] Celesto Capability 2 (Native Safety Callbacks): `CelestoSafetyCallback` subclasses `celesto.callbacks.Callback` and vetoes dangerous commands via `on_pre_run` raising `CommandBlockedError`.
- [x] Guaranteed sandbox cleanup in `try/finally` blocks and state tracking to `deleted`.
- [x] Strict sandbox naming convention enforced: `^sbx-[a-z0-9]{8,}$`.

### Trusted Control Plane (FastAPI Backend)
- [x] `GET /health` returning `{"status": "ok"}`.
- [x] `GET /api/runs` returning all ledger records including seeded `sbx-seeddemo1`.
- [x] `POST /api/runs` accepting `run_id`, `sandbox_name`, `problem_id`, `state`, `execution_target`.
- [x] Strict validation rejecting `execution_target == "host"` with HTTP 400 / 422.
- [x] `POST /api/execute` executing code exclusively inside Celesto sandboxes.
- [x] `POST /api/agent/run` multi-turn tool-calling agent endpoint.
- [x] `GET /api/reports` returning all 8 submission report artifacts.
- [x] Simple, responsive HTML dashboard served at root `/`.

### PostgreSQL Ledger & Command Audit Logging
- [x] Seed SQL in `seeds/01_runs.sql` creating schema and seeding `sbx-seeddemo1`.
- [x] Parameterized SQL queries for runs table with resilient in-memory fallback.
- [x] Real-time command audit logger writing JSONL events to `logs/commands.jsonl`.

### AI Agent
- [x] OpenAI-compatible tool calling exposing restricted `execute_code` tool.
- [x] Multi-turn dialogue with tool outputs fed back to model.
- [x] Clearly labelled deterministic testing mode when `LLM_API_KEY` is unconfigured.
- [x] Zero API key injection into untrusted guest sandboxes.

### Security & Containment
- [x] Independent regex & AST security policy blocking host escape, prompt injection, and destructive commands.
- [x] Outbound egress exfiltration blocking using synthetic canary tokens (`CANARY_TOKEN_SAFEEXEC_98a7f012bce`). Real secrets never exposed.
- [x] Four containment attack scenarios verified with evidence files in `reports/evidence/`.

### State & Failure Recovery
- [x] 10-step simulated workflow deliberately failing step 7.
- [x] Implemented 'resume' policy leveraging Celesto persistent workspace.
- [x] Complete event trace recorded in `reports/failure_trace.jsonl` with `policy_applied` event.
- [x] `reports/failure_policy.json` and comprehensive post-mortem in `reports/postmortem.md`.

### Evaluation & Reports
- [x] 20-run reliability benchmark with fresh sandboxes and exact statistical metrics in `reports/reliability.json`.
- [x] 5-job concurrency evaluation in `reports/concurrency.json`.
- [x] Complete `reports/problem.json`, `reports/capabilities.json`, `reports/lifecycle.json`.
- [x] 100% of required report schemas and evidence paths verified.

---

## 2. Pending Functionality & Cloud Verification

- [ ] **Live Celesto Cloud Cluster Runs:** Running live jobs against a paid Celesto Cloud endpoint requires the user to populate `CELESTO_API_KEY` in `.env`.
- [ ] **Live LLM Agent Conversations:** Live multi-turn LLM reasoning requires setting `LLM_API_KEY` in `.env`.

---

## 3. Commands Executed & Test Results

### Test Execution Summary
- `pytest tests/test_api.py tests/test_security.py tests/test_agent.py tests/test_reports.py`:
  - **Passed:** 23 / 23 (100% pass rate)
  - **Duration:** 3.57 seconds
- `python sandbox_smoke.py`:
  - **Status:** PASSED (Environment check, unique naming, guest execution, safety callback veto, workspace persistence verified).
- `python demo/run_demo.py`:
  - **Status:** PASSED (All 7 walkthrough steps demonstrated end-to-end in 2.02 seconds).

---

## 4. Known Errors & Mitigations

1. **Windows 260-character MAX_PATH Error:**
   - *Issue:* Celesto's nested API client file paths exceeded Windows default 260-character limit during `pip install`.
   - *Resolution:* Configured short virtual environment root at `D:\sv`, reducing path lengths well below limits.
2. **Platform Incompatibilities (`pwd`, `celesto-core` QEMU):**
   - *Issue:* Windows lacks the Unix `pwd` module and cannot host the local microVM Firecracker/KVM binary.
   - *Resolution:* Implemented standard Python compatibility stubs for `pwd` and `celesto_core` allowing the Celesto Cloud client SDK to operate smoothly on Windows.
3. **Campus Wi-Fi DNS Timeout on 8.8.8.8:**
   - *Issue:* University network blocked UDP port 53 to 8.8.8.8.
   - *Resolution:* Utilized Cloudflare DNS (1.1.1.1) and cached pip wheels.
