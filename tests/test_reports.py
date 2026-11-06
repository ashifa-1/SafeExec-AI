"""Comprehensive Report Validation Suite for SafeExec AI.

Validates that all mandatory report files, schemas, statistics,
naming conventions, and evidence files exist and strictly adhere to specifications.
"""

import json
import re
from pathlib import Path
from app.config import settings

REPORTS_DIR = settings.reports_dir


def test_problem_report():
    """Validate reports/problem.json schema and required fields."""
    file_path = REPORTS_DIR / "problem.json"
    assert file_path.exists(), "reports/problem.json is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for field in ["who", "agent_work", "proof_output", "idea_source"]:
        assert field in data, f"Missing field '{field}' in reports/problem.json"
        assert len(str(data[field]).strip()) > 10, f"Field '{field}' content is too brief"


def test_capabilities_report():
    """Validate reports/capabilities.json has >= 2 entries, evidence files, and >= 80 char explanations."""
    file_path = REPORTS_DIR / "capabilities.json"
    assert file_path.exists(), "reports/capabilities.json is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    caps = data.get("capabilities", [])
    assert len(caps) >= 2, "reports/capabilities.json must contain at least 2 unique capabilities"

    for cap in caps:
        assert "name" in cap
        assert "evidence_path" in cap
        assert "explanation" in cap

        # Explanation length check
        assert len(cap["explanation"]) >= 80, (
            f"Explanation for '{cap['name']}' must be at least 80 characters (found {len(cap['explanation'])})"
        )

        # Evidence file must exist
        ev_path = settings.base_dir / cap["evidence_path"]
        assert ev_path.exists(), f"Evidence file not found: {ev_path}"


def test_lifecycle_report():
    """Validate reports/lifecycle.json cleanup guarantees and naming conventions."""
    file_path = REPORTS_DIR / "lifecycle.json"
    assert file_path.exists(), "reports/lifecycle.json is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("cleanup_on_success") is True
    assert data.get("cleanup_on_failure") is True
    assert data.get("cleanup_on_interrupt") is True

    names = data.get("sandbox_names", [])
    assert len(names) >= 1
    for name in names:
        assert re.match(r"^sbx-[a-z0-9]{8,}$", name), (
            f"Sandbox name '{name}' does not match sbx-[a-z0-9]{{8,}}"
        )


def test_reliability_report():
    """Validate reports/reliability.json contains 20 runs and accurate statistics."""
    file_path = REPORTS_DIR / "reliability.json"
    assert file_path.exists(), "reports/reliability.json is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    runs = data.get("runs", [])
    assert len(runs) >= 20, f"Must have at least 20 runs in reliability report (found {len(runs)})"

    seen_names = set()
    for r in runs:
        assert r.get("fresh") is True, "Each reliability run must have fresh=true"
        name = r.get("sandbox_name", "")
        assert re.match(r"^sbx-[a-z0-9]{8,}$", name), f"Invalid sandbox name format: {name}"
        assert name not in seen_names, f"Duplicate sandbox name in reliability test: {name}"
        seen_names.add(name)
        assert "wall_clock_s" in r
        assert "boot_to_ready_s" in r
        assert "cost_usd" in r
        assert "success" in r

    # Validate calculated fields
    for field in [
        "run_count",
        "success_rate",
        "median_wall_clock_s",
        "p90_wall_clock_s",
        "median_boot_to_ready_s",
        "total_cost_usd"
    ]:
        assert field in data, f"Missing statistic field '{field}' in reliability report"

    assert data["run_count"] == len(runs)
    assert 0.0 <= data["success_rate"] <= 1.0


def test_postmortem_report():
    """Validate reports/postmortem.md has at least 200 characters."""
    file_path = REPORTS_DIR / "postmortem.md"
    assert file_path.exists(), "reports/postmortem.md is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert len(content.strip()) >= 200, (
        f"reports/postmortem.md must have at least 200 characters (found {len(content.strip())})"
    )


def test_containment_report():
    """Validate reports/containment.json and verify all evidence files exist."""
    file_path = REPORTS_DIR / "containment.json"
    assert file_path.exists(), "reports/containment.json is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("host_untouched") is True
    assert "evidence_paths" in data

    for ev_rel in data["evidence_paths"]:
        ev_file = REPORTS_DIR / ev_rel
        assert ev_file.exists(), f"Containment evidence file does not exist: {ev_file}"

    tests = data.get("tests", [])
    assert len(tests) >= 1
    for t in tests:
        assert "attack" in t
        assert "blocked" in t
        assert "host_untouched" in t


def test_failure_policy_and_trace():
    """Validate reports/failure_policy.json and failure_trace.jsonl step 7 recovery."""
    policy_file = REPORTS_DIR / "failure_policy.json"
    trace_file = REPORTS_DIR / "failure_trace.jsonl"

    assert policy_file.exists(), "reports/failure_policy.json is missing"
    assert trace_file.exists(), "reports/failure_trace.jsonl is missing"

    with open(policy_file, "r", encoding="utf-8") as f:
        pdata = json.load(f)

    assert pdata.get("failed_step") == 7, "failed_step must strictly equal 7"
    assert pdata.get("total_steps") == 10, "total_steps must strictly equal 10"
    assert pdata.get("policy") in ["resume", "rollback", "fresh"]
    assert len(pdata.get("rationale", "")) >= 200, "Rationale must be at least 200 characters"

    # Validate trace events
    events = []
    with open(trace_file, "r", encoding="utf-8") as tf:
        for line in tf:
            if line.strip():
                events.append(json.loads(line))

    assert len(events) >= 10, "failure_trace.jsonl must contain at least 10 lifecycle events"

    # Verify policy_applied event exists with matching policy
    policy_applied_events = [e for e in events if e.get("event_type") == "policy_applied"]
    assert len(policy_applied_events) >= 1, "Must contain a 'policy_applied' event in failure_trace.jsonl"
    assert policy_applied_events[0].get("policy") == pdata["policy"]
    assert policy_applied_events[0].get("step") == 7


def test_concurrency_report():
    """Validate reports/concurrency.json contains 5 jobs with unique sandbox names and ISO timestamps."""
    file_path = REPORTS_DIR / "concurrency.json"
    assert file_path.exists(), "reports/concurrency.json is missing"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    assert len(jobs) == 5, f"reports/concurrency.json must contain exactly 5 jobs (found {len(jobs)})"

    seen_names = set()
    for job in jobs:
        name = job.get("sandbox_name", "")
        assert re.match(r"^sbx-[a-z0-9]{8,}$", name), f"Invalid sandbox name format: {name}"
        assert name not in seen_names, f"Duplicate sandbox name in concurrency test: {name}"
        seen_names.add(name)

        # Check ISO-8601 timestamps
        assert "started_at" in job
        assert "ended_at" in job

    assert "account_limitation_notes" in data

