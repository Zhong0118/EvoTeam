"""稳定 AgentConfig 与只属于某次 Run 的 AgentInstance。"""

from enum import StrEnum

from pydantic import Field, JsonValue

from evoteam.domain.common import (
    AssetRef,
    DomainModel,
    FrozenModel,
    Identifier,
    NonNegativeInt,
    PositiveFloat,
)
from evoteam.domain.role import RoleType


class ToolPolicy(FrozenModel):
    allowed_tools: tuple[AssetRef, ...] = ()
    required_tools: tuple[AssetRef, ...] = ()
    # TODO(P0): 校验 required 是 allowed 子集，定义条件调用规则。


class RuntimeConfig(FrozenModel):
    """初始不指定模型运行参数；运行前由开发者显式配置。"""

    timeout_seconds: PositiveFloat | None = None
    max_retries: NonNegativeInt = 0


class AgentConfig(FrozenModel):
    node_id: Identifier
    config_id: Identifier
    config_version: NonNegativeInt
    role: RoleType
    prompt_ref: AssetRef
    model_ref: AssetRef
    skill_refs: tuple[AssetRef, ...] = ()
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig)


class AgentState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class AgentMessage(DomainModel):
    """结构化信封；各 Role 的具体 payload Schema 在任务实现时收紧。"""

    message_id: Identifier
    sender_node_id: Identifier | None = None
    recipient_node_id: Identifier
    schema_ref: AssetRef
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    source_event_ids: tuple[str, ...] = ()


class AgentResult(DomainModel):
    instance_id: Identifier
    output_schema: AssetRef
    output: dict[str, JsonValue]
    tool_result_refs: tuple[str, ...] = ()
    input_tokens: NonNegativeInt | None = None
    output_tokens: NonNegativeInt | None = None


class AgentInstance(DomainModel):
    instance_id: Identifier
    run_id: Identifier
    task_id: Identifier
    config: AgentConfig
    state: AgentState = AgentState.CREATED
    context: dict[str, JsonValue] = Field(default_factory=dict)
    messages: list[AgentMessage] = Field(default_factory=list)
    tool_result_refs: list[str] = Field(default_factory=list)
    result: AgentResult | None = None
