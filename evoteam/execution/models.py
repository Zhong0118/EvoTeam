"""网页执行作业契约（F0）：提交请求、状态视图与增量事件信封。

字段与不变式来自 docs/TASK_PRESENTATION.md §3。作业状态与 Domain RunStatus
分离：interrupted 只表示进程遗留作业，不伪造成已封存 Run；completed 仅代表
流程完成并封存，评价 success=false 仍是合法的 completed 作业。
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, JsonValue, model_validator

from evoteam.domain.agent import AgentState
from evoteam.domain.common import (
    DomainModel,
    FrozenModel,
    Identifier,
    NonNegativeInt,
    StrategyRef,
)
from evoteam.domain.planning import parse_planning_task
from evoteam.domain.task import Task


class SubmitExecution(DomainModel):
    """网页任务提交信封；接收前即按 project-planning-input@1 完成校验。"""

    request_id: UUID
    strategy_id: Identifier
    task: Task

    @model_validator(mode="after")
    def validate_supported_task(self) -> Self:
        parse_planning_task(self.task)
        return self


class ExecutionStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ExecutionPhase(StrEnum):
    """后端真实阶段；前端不得据此推算完成百分比或预计费用。"""

    ACCEPTED = "accepted"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    SEALING = "sealing"
    TERMINAL = "terminal"


_TERMINAL_STATUSES = frozenset(
    {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.TIMED_OUT,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.INTERRUPTED,
    }
)


class ExecutionView(FrozenModel):
    """作业状态视图；时间、引用与错误均为安全投影，不含凭据或内部路径。"""

    execution_id: Identifier
    run_id: Identifier
    strategy_id: Identifier
    status: ExecutionStatus
    phase: ExecutionPhase
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    strategy_ref: StrategyRef | None = None
    last_sequence: Annotated[int, Field(ge=-1)] = -1
    sealed_run_id: Identifier | None = None
    error_code: str | None = None
    safe_message: str | None = None
    cancel_requested: bool = False

    @model_validator(mode="after")
    def check_lifecycle(self) -> Self:
        terminal = self.status in _TERMINAL_STATUSES
        if terminal != (self.phase is ExecutionPhase.TERMINAL):
            raise ValueError("terminal 阶段必须与终态状态一致")
        if terminal:
            if self.finished_at is None:
                raise ValueError("终态作业必须记录 finished_at")
            if self.status is ExecutionStatus.COMPLETED and self.sealed_run_id is None:
                raise ValueError("completed 作业必须引用封存 Run")
            if self.status is ExecutionStatus.INTERRUPTED and self.sealed_run_id is not None:
                raise ValueError("interrupted 作业不得伪造封存 Run")
            return self
        if self.sealed_run_id is not None or self.finished_at is not None:
            raise ValueError("未终态作业不得引用封存 Run 或结束时间")
        if self.status is ExecutionStatus.ACCEPTED:
            if self.started_at is not None:
                raise ValueError("accepted 作业尚未开始执行")
            if self.phase is not ExecutionPhase.ACCEPTED:
                raise ValueError("accepted 状态对应 accepted 阶段")
        elif self.status is ExecutionStatus.RUNNING:
            if self.started_at is None:
                raise ValueError("running 作业必须记录开始时间")
            if self.phase is ExecutionPhase.ACCEPTED:
                raise ValueError("running 作业不能停留在 accepted 阶段")
        return self


class TraceEventView(DomainModel):
    """增量事件投影；延续事件身份与因果字段，仅暴露白名单内容。"""

    event_id: Identifier
    event_type: str
    timestamp: datetime
    sequence: NonNegativeInt
    run_id: str | None = None
    node_id: str | None = None
    instance_id: str | None = None
    caused_by: tuple[str, ...] = ()
    node_state: AgentState | None = None
    output: dict[str, JsonValue] | None = None
    config: dict[str, JsonValue] | None = None


class ExecutionEventsPage(DomainModel):
    """游标分页的增量事件信封；next_after_sequence 是真实服务端事件游标。"""

    items: tuple[TraceEventView, ...] = ()
    next_after_sequence: Annotated[int, Field(ge=-1)] = -1
    terminal: bool = False
