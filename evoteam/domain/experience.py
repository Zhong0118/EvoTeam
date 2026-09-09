"""正负经验与归因报告；证据不足时保留不确定性。"""

from enum import StrEnum

from evoteam.domain.common import FrozenModel, Identifier, Probability, StrategyRef


class AttributionKind(StrEnum):
    ORIGIN = "origin"
    CONTROL = "control"
    CONTRIBUTION = "contribution"
    IMPROVEMENT = "improvement"


class AttributionClaim(FrozenModel):
    kind: AttributionKind
    target: Identifier
    explanation: str
    confidence: Probability
    evidence_refs: tuple[str, ...]


class AttributionReport(FrozenModel):
    report_id: Identifier
    strategy: StrategyRef
    task_scope: Identifier
    claims: tuple[AttributionClaim, ...]
    needs_more_evidence: bool


class FailureExperience(FrozenModel):
    experience_id: Identifier
    strategy: StrategyRef
    task_scope: Identifier
    failure_pattern: Identifier
    supporting_runs: tuple[str, ...]
    counterexample_runs: tuple[str, ...] = ()
    attribution_ref: str | None = None
    confidence: Probability | None = None


class ImprovementExperience(FrozenModel):
    experience_id: Identifier
    current: StrategyRef
    candidate: StrategyRef
    task_scope: Identifier
    mutation_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    quality_delta: float | None = None
    token_delta: float | None = None
    latency_delta_seconds: float | None = None
    counterexample_runs: tuple[str, ...] = ()


class OutcomePattern(FrozenModel):
    pattern_id: Identifier
    strategy: StrategyRef
    task_scope: Identifier
    supporting_runs: tuple[str, ...]
    failures: tuple[FailureExperience, ...] = ()
    improvements: tuple[ImprovementExperience, ...] = ()
    contribution_report_refs: tuple[str, ...] = ()
