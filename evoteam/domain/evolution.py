"""Trigger、Mutation、实验与治理结果的数据契约，不执行决策。"""

from enum import StrEnum

from evoteam.domain.common import (
    AssetRef,
    FrozenModel,
    Identifier,
    NonNegativeFloat,
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
    """受白名单约束的最小修改提案；首版只执行 UPDATE_PROMPT。"""

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


class ValidationPair(FrozenModel):
    """一次同任务、同重复序号的 Current/Candidate 封存对。"""

    task_id: Identifier
    task_fingerprint: str
    subclass: Identifier
    repeat_index: NonNegativeInt
    current_run_id: Identifier
    candidate_run_id: Identifier
    current_metrics: RunMetrics
    candidate_metrics: RunMetrics


class LatencyDistribution(FrozenModel):
    """nearest-rank 分位数；p95 样本少于 20 时只记录、不作稳定性结论。"""

    sample_count: NonNegativeInt
    p50_seconds: NonNegativeFloat | None = None
    p95_seconds: NonNegativeFloat | None = None
    algorithm: str = "nearest_rank"


class SubclassValidationSummary(FrozenModel):
    subclass: Identifier
    success_count: NonNegativeInt
    total_count: NonNegativeInt
    unknown_success_count: NonNegativeInt
    independent_task_count: NonNegativeInt
    latency: LatencyDistribution


class ValidationSummary(FrozenModel):
    success_count: NonNegativeInt
    total_count: NonNegativeInt
    unknown_success_count: NonNegativeInt
    independent_task_count: NonNegativeInt
    subclasses: tuple[SubclassValidationSummary, ...]
    latency: LatencyDistribution


class ValidationSampling(FrozenModel):
    repeats: PositiveInt
    seeds: tuple[int, ...]
    seed_applied: bool


class ValidationResult(FrozenModel):
    validation_id: Identifier
    current: StrategyRef
    candidate: StrategyRef
    plan: ValidationPlan
    current_run_ids: tuple[str, ...]
    candidate_run_ids: tuple[str, ...]
    current_metrics: RunMetrics
    candidate_metrics: RunMetrics
    pairs: tuple[ValidationPair, ...] = ()
    current_summary: ValidationSummary | None = None
    candidate_summary: ValidationSummary | None = None
    sampling: ValidationSampling | None = None
    limitations: tuple[str, ...] = ()


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
    termination_reason: str | None = None
