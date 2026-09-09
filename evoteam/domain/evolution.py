"""Trigger、Mutation、实验与治理结果的数据契约，不执行决策。"""

from enum import StrEnum

from evoteam.domain.common import (
    AssetRef,
    FrozenModel,
    Identifier,
    NonNegativeInt,
    PositiveInt,
    StrategyRef,
)
from evoteam.domain.evaluation import RunMetrics


class TriggerType(StrEnum):
    REPEATED_FAILURE = "repeated_failure"
    PERFORMANCE_DRIFT = "performance_drift"
    HIGH_COST = "high_cost"
    LOW_CONTRIBUTION = "low_contribution"
    DISTRIBUTION_CHANGE = "distribution_change"


class EvolutionTrigger(FrozenModel):
    trigger_id: Identifier
    strategy: StrategyRef
    policy_ref: AssetRef
    trigger_type: TriggerType
    task_scope: Identifier
    evidence_run_ids: tuple[str, ...]
    reason: str


class MonitorResult(FrozenModel):
    strategy: StrategyRef
    sample_count: NonNegativeInt
    reason: str
    trigger: EvolutionTrigger | None = None


class MutationType(StrEnum):
    ADD_AGENT_CONFIG = "add_agent_config"
    REMOVE_AGENT_CONFIG = "remove_agent_config"
    REPLACE_AGENT_CONFIG = "replace_agent_config"
    UPDATE_PROMPT = "update_prompt"
    UPDATE_TOOL_POLICY = "update_tool_policy"
    REWIRE = "rewire"
    CONDITIONALIZE = "conditionalize"


class MutationProposal(FrozenModel):
    """提案描述；操作专属 payload/schema 与执行器留到 P3。"""

    proposal_id: Identifier
    parent: StrategyRef
    operation: MutationType
    target: Identifier
    rationale: str
    attribution_ref: Identifier
    replacement_ref: AssetRef | None = None


class GateDecision(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    CONTINUE_SAMPLING = "continue_sampling"
    NARROW_SCOPE = "narrow_scope"


class ValidationPlan(FrozenModel):
    """验证数据只通过不可变引用交给 Validator，不给 Candidate Generator。"""

    dataset_ref: AssetRef
    evaluator_ref: AssetRef
    repeats: PositiveInt
    seeds: tuple[int, ...]
    # TODO(P4): 登记模型/工具/预算及子类切分的完整实验清单。


class ValidationResult(FrozenModel):
    validation_id: Identifier
    current: StrategyRef
    candidate: StrategyRef
    plan: ValidationPlan
    current_run_ids: tuple[str, ...]
    candidate_run_ids: tuple[str, ...]
    current_metrics: RunMetrics
    candidate_metrics: RunMetrics
    # 单 Run 指标之外的分布、置信区间与子类统计在 P4 增补。


class GateResult(FrozenModel):
    validation_id: Identifier
    decision: GateDecision
    policy_ref: AssetRef
    reasons: tuple[str, ...]
    improvement_attribution_ref: Identifier


class EvolutionRecord(FrozenModel):
    evolution_id: Identifier
    trigger: EvolutionTrigger
    attribution_refs: tuple[str, ...] = ()
    proposal_refs: tuple[str, ...] = ()
    candidates: tuple[StrategyRef, ...] = ()
    validation_refs: tuple[str, ...] = ()
    gate_results: tuple[GateResult, ...] = ()
    promoted: StrategyRef | None = None
    rollback_target: StrategyRef | None = None
