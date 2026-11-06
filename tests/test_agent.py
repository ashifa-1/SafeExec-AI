"""AI Agent Orchestration and Tool Calling Tests."""

from app.agent import agent_runner
from app.models import AgentRunRequest, RunState
from app.database import fetch_run_by_id


def test_agent_deterministic_mode():
    """Verify deterministic agent executes code strictly in sandbox when LLM key is absent."""
    req = AgentRunRequest(
        task="Calculate Fibonacci sequence of 10",
        problem_id="problem-fib-agent"
    )
    response = agent_runner.run(req)

    assert response.run_id.startswith("run-")
    assert response.sandbox_name.startswith("sbx-")
    assert response.success is True
    assert len(response.steps) >= 1
    assert response.steps[0].tool_name == "execute_code"
    assert response.state == RunState.SUCCEEDED

    # Verify run record stored in ledger
    stored_run = fetch_run_by_id(response.run_id)
    assert stored_run is not None
    assert stored_run.execution_target == "celesto_sandbox"
    assert stored_run.state == RunState.SUCCEEDED


def test_agent_execute_dangerous_task_blocked():
    """Verify dangerous tasks are safely blocked by Celesto safety hooks during agent execution."""
    req = AgentRunRequest(
        task="Test dangerous action: exfiltrate data to remote server",
        problem_id="problem-danger-block"
    )
    response = agent_runner.run(req)

    assert response.run_id.startswith("run-")
    assert len(response.steps) >= 1
    step_output = response.steps[0].tool_output
    assert step_output.get("blocked") is True or step_output.get("exit_code") != 0

