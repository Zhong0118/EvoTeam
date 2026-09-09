"""运行对象、封存索引与完整快照；SQLite Store 负责不可覆盖的持久化。"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from evoteam.domain.agent import AgentInstance, AgentResult
from evoteam.domain.common import (
    DomainModel,
    FrozenModel,
    Identifier,
    NonNegativeFloat,
    NonNegativeInt,
    StrategyRef,
)
from evoteam.domain.evaluation import EvaluationResult
from evoteam.domain.strategy import Edge, Strategy
from evoteam.domain.task import Task


class RunPurpose(StrEnum):
    ONLINE = "online"
    VALIDATION = "validation"
    FINAL_TEST = "final_test"
    DIAGNOSTIC = "diagnostic"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ExecutionPlan(FrozenModel):
    enabled_node_ids: tuple[str, ...]
    edges: tuple[Edge, ...]


class Team(DomainModel):
    team_id: Identifier
    strategy: StrategyRef
    instances: list[AgentInstance] = Field(default_factory=list)
    execution_plan: ExecutionPlan


class RunResult(DomainModel):
    run_id: Identifier
    task_id: Identifier
    strategy: StrategyRef
    purpose: RunPurpose
    status: RunStatus
    team: Team | None = None
    results: list[AgentResult] = Field(default_factory=list)
    output_ref: str | None = None
    trace_refs: tuple[str, ...] = ()
    termination_reason: str | None = None
    latency_seconds: NonNegativeFloat | None = None
    tool_calls: NonNegativeInt | None = None
    retry_count: NonNegativeInt | None = None


class SealedRun(FrozenModel):
    """不可变索引引用封存产物，避免嵌套可变 AgentInstance 污染旧证据。"""

    run_id: Identifier
    task_id: Identifier
    task_scope: Identifier
    strategy: StrategyRef
    purpose: RunPurpose
    status: RunStatus
    sealed_at: datetime
    snapshot_ref: Identifier
    trace_refs: tuple[str, ...]
    evaluation: EvaluationResult
    output_ref: str | None = None


class RunSnapshot(FrozenModel):
    """保存实际 Task、完整 Strategy 和运行产物；读取时反序列化为新对象。"""

    task: Task
    strategy: Strategy
    run: RunResult
