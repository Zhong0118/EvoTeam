"""单 Run 评价结果；未知指标用 None，不能伪装成零成本或成功。"""

from evoteam.domain.common import (
    AssetRef,
    FrozenModel,
    Identifier,
    NonNegativeFloat,
    NonNegativeInt,
)


class EvaluationIssue(FrozenModel):
    code: Identifier
    message: str
    severity: str
    evidence_refs: tuple[str, ...] = ()
    node_id: str | None = None


class RunMetrics(FrozenModel):
    """quality 的尺度由 evaluator_ref 所指协议确定，当前不预设权重。"""

    quality: float | None = None
    success: bool | None = None
    hard_constraint_errors: NonNegativeInt | None = None
    tokens: NonNegativeInt | None = None
    cost: NonNegativeFloat | None = None
    latency_seconds: NonNegativeFloat | None = None
    agent_count: NonNegativeInt | None = None
    tool_calls: NonNegativeInt | None = None
    retry_count: NonNegativeInt | None = None


class EvaluationResult(FrozenModel):
    run_id: Identifier
    evaluator_ref: AssetRef
    metrics: RunMetrics
    issues: tuple[EvaluationIssue, ...] = ()
    missing_metrics: tuple[str, ...] = ()
