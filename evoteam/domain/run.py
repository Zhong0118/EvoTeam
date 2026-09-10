"""运行对象、封存索引与完整快照；SQLite Store 负责不可覆盖的持久化。"""

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from evoteam.domain.agent import AgentInstance, AgentResult
from evoteam.domain.common import (
    DomainModel,
    FrozenModel,
    Identifier,
    NonNegativeFloat,
    NonNegativeInt,
    StrategyRef,
)
from evoteam.domain.dataset import DatasetPartition, DatasetSource, task_fingerprint
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
    dataset_source: DatasetSource | None = None
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
    dataset_source: DatasetSource | None = None
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

    @model_validator(mode="after")
    def verify_dataset_source(self) -> Self:
        validate_run_source(self.task, self.run)
        return self


def validate_run_source(task: Task, run: RunResult) -> None:
    """Legacy runs may lack provenance; declared sources must match execution."""
    source = run.dataset_source
    if source is None:
        return
    expected = {
        RunPurpose.ONLINE: DatasetPartition.HISTORY,
        RunPurpose.VALIDATION: DatasetPartition.VALIDATION,
        RunPurpose.FINAL_TEST: DatasetPartition.FINAL_TEST,
    }.get(run.purpose)
    if (
        source.task_id != task.task_id
        or source.task_id != run.task_id
        or source.task_fingerprint != task_fingerprint(task)
        or (expected is not None and source.partition != expected)
    ):
        raise ValueError("Run 数据来源与 Task / Purpose 不一致")
