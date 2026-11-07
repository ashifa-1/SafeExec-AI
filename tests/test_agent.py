"""AI Agent Orchestration and Tool Calling Tests."""

import json
import time

from app.agent import SafeExecAgent, agent_runner
from app.config import settings
from app.models import AgentRunRequest, ExecuteResult, RunState
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


def test_llm_agent_executes_tool_and_returns_model_answer(monkeypatch):
    """Verify OpenAI-compatible tool calls are executed and the final answer is returned."""
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(settings, "llm_model", "test-model")

    tool_call = {
        "id": "call-1",
        "type": "function",
        "function": {
            "name": "execute_code",
            "arguments": json.dumps({"code": "print(55)", "language": "python"})
        }
    }

    class FakeResponse:
        def __init__(self, message):
            self.message = message

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": self.message}]}

    responses = iter([
        FakeResponse({"role": "assistant", "content": None, "tool_calls": [tool_call]}),
        FakeResponse({"role": "assistant", "content": "The result is 55."})
    ])
    agent = SafeExecAgent()
    requests = []

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return next(responses)

    monkeypatch.setattr(agent.client, "post", fake_post)
    monkeypatch.setattr(
        "app.agent.sandbox_runner.execute",
        lambda **kwargs: ExecuteResult(
            stdout="55\n",
            stderr="",
            exit_code=0,
            wall_clock_s=0.1,
            boot_to_ready_s=0.0,
            sandbox_name="sbx-llmtest1",
            success=True
        )
    )

    response = agent._run_llm_agent(
        AgentRunRequest(task="Calculate 55", max_iterations=2),
        "run-llm-test",
        "sbx-llmtest1",
        time.perf_counter()
    )

    assert response.success is True
    assert response.state == RunState.SUCCEEDED
    assert response.final_response == "The result is 55."
    assert response.steps[0].tool_output["stdout"] == "55\n"
    assert requests[0][0] == "https://llm.example/v1/chat/completions"
    assert requests[0][1]["headers"]["Authorization"] == "Bearer test-key"


def test_llm_agent_does_not_claim_success_without_final_answer(monkeypatch):
    """Verify exhausting iterations after execution does not fabricate a model response."""
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "execute_code",
                                "arguments": json.dumps({"code": "print(55)"})
                            }
                        }]
                    }
                }]
            }

    agent = SafeExecAgent()
    monkeypatch.setattr(agent.client, "post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(
        "app.agent.sandbox_runner.execute",
        lambda **kwargs: ExecuteResult(
            stdout="55\n",
            stderr="",
            exit_code=0,
            wall_clock_s=0.1,
            boot_to_ready_s=0.0,
            sandbox_name="sbx-llmtest1",
            success=True
        )
    )

    response = agent._run_llm_agent(
        AgentRunRequest(task="Calculate 55", max_iterations=1),
        "run-llm-test",
        "sbx-llmtest1",
        time.perf_counter()
    )

    assert response.success is False
    assert response.state == RunState.FAILED
    assert "without receiving a final answer" in response.final_response
