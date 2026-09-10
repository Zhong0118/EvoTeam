from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.evaluation import RunMetrics
from evoteam.domain.evolution import GateDecision, ValidationPair, ValidationPlan, ValidationResult
from evoteam.domain.experience import AttributionClaim, AttributionKind, AttributionReport
from evoteam.evolution.gate import GatePolicy, ValidationGate


def _result(pairs: tuple[ValidationPair, ...]) -> ValidationResult:
    return ValidationResult(
        validation_id="validation-n3",
        current=StrategyRef(strategy_id="s", version=0),
        candidate=StrategyRef(strategy_id="s", version=1),
        plan=ValidationPlan(
            dataset_ref=AssetRef(id="validation", version="1"),
            evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
            repeats=1,
            seeds=(7,),
        ),
        current_run_ids=tuple(pair.current_run_id for pair in pairs),
        candidate_run_ids=tuple(pair.candidate_run_id for pair in pairs),
        current_metrics=RunMetrics(
            success=False, hard_constraint_errors=3, tokens=20, latency_seconds=2
        ),
        candidate_metrics=RunMetrics(
            success=False, hard_constraint_errors=2, tokens=20, latency_seconds=2
        ),
        pairs=pairs,
    )


def _attribution() -> AttributionReport:
    return AttributionReport(
        report_id="report",
        strategy=StrategyRef(strategy_id="s", version=1),
        task_scope="validation",
        claims=(
            AttributionClaim(
                kind=AttributionKind.IMPROVEMENT,
                target="strategy:s@1",
                explanation="controlled observation",
                confidence=1,
                evidence_refs=("validation:validation-n3",),
            ),
        ),
        needs_more_evidence=False,
    )


def _policy(**updates) -> GatePolicy:
    policy = GatePolicy(
        ref=AssetRef(id="gate", version="n3"),
        minimum_quality_gain=0,
        maximum_quality_regression=0,
        maximum_token_increase=0,
        maximum_latency_increase=0,
        minimum_paired_runs=2,
        minimum_independent_tasks=2,
        maximum_subclass_success_regression=0,
    )
    return policy.model_copy(update=updates)


def _pair(task: str, fingerprint: str, subclass: str, before: bool, after: bool, repeat: int = 0):
    return ValidationPair(
        task_id=task,
        task_fingerprint=fingerprint,
        subclass=subclass,
        repeat_index=repeat,
        current_run_id=f"c-{task}-{repeat}",
        candidate_run_id=f"n-{task}-{repeat}",
        current_metrics=RunMetrics(
            success=before, hard_constraint_errors=0 if before else 3, tokens=10, latency_seconds=1
        ),
        candidate_metrics=RunMetrics(
            success=after, hard_constraint_errors=0 if after else 2, tokens=10, latency_seconds=1
        ),
    )


def test_aggregate_error_decline_cannot_hide_task_regression():
    result = _result(
        (_pair("task-1", "fp-1", "a", False, True), _pair("task-2", "fp-2", "b", True, False))
    )
    decision = ValidationGate().decide(result, _attribution(), _policy())
    assert decision.decision == GateDecision.FAIL
    assert any("task-2" in reason for reason in decision.reasons)


def test_repeats_do_not_increase_independent_task_count():
    pairs = tuple(_pair("task-1", "same", "a", False, True, repeat) for repeat in range(2))
    result = _result(pairs)
    decision = ValidationGate().decide(result, _attribution(), _policy())
    assert decision.decision == GateDecision.CONTINUE_SAMPLING
    assert any("独立任务数=1" in reason for reason in decision.reasons)


def test_legacy_aggregate_record_cannot_masquerade_as_pair_evidence():
    legacy = _result(())
    legacy = legacy.model_copy(
        update={"current_run_ids": ("c1", "c2"), "candidate_run_ids": ("n1", "n2")}
    )
    decision = ValidationGate().decide(legacy, _attribution(), _policy())
    assert decision.decision == GateDecision.CONTINUE_SAMPLING
    assert any("旧聚合记录" in reason for reason in decision.reasons)
