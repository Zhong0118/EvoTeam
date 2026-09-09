"""组织定义与版本信息；不持有 SDK Agent 或运行时上下文。"""

from enum import StrEnum

from pydantic import Field

from evoteam.domain.agent import AgentConfig
from evoteam.domain.common import (
    AssetRef,
    FrozenModel,
    Identifier,
    NonNegativeInt,
    RunBudget,
    StrategyRef,
)


class StrategyStatus(StrEnum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    CURRENT = "current"
    STABLE = "stable"
    REJECTED = "rejected"
    RETIRED = "retired"
    ROLLED_BACK = "rolled_back"


class ExecutionMode(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class Edge(FrozenModel):
    source: Identifier
    target: Identifier
    condition_ref: AssetRef | None = None


class OrchestrationPolicy(FrozenModel):
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    retry_limit: NonNegativeInt = 0
    replan_limit: NonNegativeInt = 0
    budget: RunBudget = Field(default_factory=RunBudget)
    # TODO(P0/P1): 注册可观测条件与 stop/routing 规则；不执行任意表达式。


class StrategyDefinition(FrozenModel):
    agents: tuple[AgentConfig, ...] = Field(min_length=1)
    edges: tuple[Edge, ...] = ()
    orchestration: OrchestrationPolicy = Field(default_factory=OrchestrationPolicy)
    # TODO(P0): 节点唯一性、悬空边、图结构、权限及预算检查。


class StrategyVersionMetadata(FrozenModel):
    ref: StrategyRef
    parent: StrategyRef | None = None
    generation: NonNegativeInt = 0
    status: StrategyStatus = StrategyStatus.DRAFT


class Strategy(FrozenModel):
    definition: StrategyDefinition
    metadata: StrategyVersionMetadata
