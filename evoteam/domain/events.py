"""统一事件名称与信封；在线及治理事件共用可追溯身份。"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue

from evoteam.domain.common import DomainModel, Identifier, NonNegativeInt, StrategyRef


class EventType(StrEnum):
    TASK_CREATED = "task_created"
    TEAM_CREATED = "team_created"
    AGENT_STARTED = "agent_started"
    AGENT_MESSAGE = "agent_message"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    RUN_FINISHED = "run_finished"
    EVALUATION_COMPLETED = "evaluation_completed"
    RUN_SEALED = "run_sealed"
    EVOLUTION_TRIGGERED = "evolution_triggered"
    ATTRIBUTION_COMPLETED = "attribution_completed"
    CANDIDATE_CREATED = "candidate_created"
    VALIDATION_COMPLETED = "validation_completed"
    GATE_DECIDED = "gate_decided"
    STRATEGY_PROMOTED = "strategy_promoted"
    STRATEGY_REJECTED = "strategy_rejected"
    STRATEGY_STABLE = "strategy_stable"
    EVOLUTION_REOPENED = "evolution_reopened"
    STRATEGY_ROLLED_BACK = "strategy_rolled_back"


class TraceEvent(DomainModel):
    event_id: Identifier
    event_type: EventType
    timestamp: datetime
    sequence: NonNegativeInt
    strategy: StrategyRef
    run_id: str | None = None
    task_id: str | None = None
    evolution_id: str | None = None
    node_id: str | None = None
    instance_id: str | None = None
    caused_by: tuple[str, ...] = ()
    payload: dict[str, JsonValue] = Field(default_factory=dict)
