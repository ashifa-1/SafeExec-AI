"""Pydantic schemas and models for SafeExec AI."""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class RunState(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DELETED = "deleted"


class ExecutionTarget(str, Enum):
    CELESTO_SANDBOX = "celesto_sandbox"


class RunBase(BaseModel):
    run_id: str = Field(..., description="Unique run identifier")
    sandbox_name: str = Field(
        ...,
        description="Unique sandbox name adhering to sbx-[a-z0-9]{8,}"
    )
    problem_id: str = Field(..., description="Identifier for task or problem")
    state: RunState = Field(..., description="Lifecycle state of the run")
    execution_target: str = Field(
        ...,
        description="Must be 'celesto_sandbox'. Host execution is strictly forbidden."
    )

    @field_validator("execution_target")
    @classmethod
    def validate_execution_target(cls, v: str) -> str:
        if v != "celesto_sandbox":
            raise ValueError("execution_target must equal 'celesto_sandbox'. Host execution is prohibited.")
        return v

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        import re
        if not re.match(r"^sbx-[a-z0-9]{8,}$", v):
            raise ValueError("sandbox_name must begin with 'sbx-' followed by at least 8 lowercase alphanumeric characters")
        return v


class RunCreate(RunBase):
    success: Optional[bool] = None
    execution_time: Optional[float] = None


class RunResponse(RunBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    success: Optional[bool] = None
    execution_time: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ExecuteRequest(BaseModel):
    code: str = Field(..., description="Code snippet or command to execute in sandbox")
    language: str = Field(default="python", description="Language: python, bash, sh")
    timeout_s: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds")
    sandbox_name: Optional[str] = Field(
        default=None,
        description="Specific sandbox name (format sbx-[a-z0-9]{8,}) or auto-generated if omitted"
    )
    persistent: bool = Field(default=False, description="Whether to preserve sandbox across calls")


class ExecuteResult(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    wall_clock_s: float = 0.0
    boot_to_ready_s: float = 0.0
    sandbox_name: str
    success: bool
    blocked: bool = False
    security_reason: Optional[str] = None
    error: Optional[str] = None


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=3, description="Natural-language coding task")
    problem_id: Optional[str] = Field(default="task-default", description="Associated problem ID")
    max_iterations: int = Field(default=5, ge=1, le=15, description="Maximum agent tool-calling iterations")
    sandbox_name: Optional[str] = Field(default=None, description="Optional sandbox name")
    persistent: bool = Field(default=False, description="Whether sandbox persists between tool steps")


class AgentStep(BaseModel):
    step_number: int
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    tool_output: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentRunResponse(BaseModel):
    run_id: str
    problem_id: str
    sandbox_name: str
    task: str
    final_response: str
    steps: list[AgentStep] = []
    success: bool
    total_wall_clock_s: float
    state: RunState

