"""审查发现的 Gate 放行边界，使用真实归因和规则裁决。"""

import pytest

from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.evaluation import RunMetrics
from evoteam.domain.evolution import GateDecision, ValidationPlan, ValidationResult
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.gate import GatePolicy, ValidationGate


def result_for(before: RunMetrics, after: RunMetrics) -> ValidationResult:
    return ValidationResult(
        validation_id="paired",
        current=StrategyRef(strategy_id="planning", version=0),
        candidate=StrategyRef(strategy_id="planning", version=1),
        plan=ValidationPlan(
            dataset_ref=AssetRef(id="held-out", version="1"),
            evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
            repeats=2,
            seeds=(1, 2),
        ),
        current_run_ids=("before-1", "before-2"),
        candidate_run_ids=("after-1", "after-2"),
        current_metrics=before,
        candidate_metrics=after,
    )


def policy() -> GatePolicy:
    return GatePolicy(
        ref=AssetRef(id="gate", version="review"),
        minimum_quality_gain=0,
        maximum_quality_regression=0,
        maximum_token_increase=0,
        maximum_latency_increase=0,
        minimum_paired_runs=2,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["tokens", "latency_seconds"])
async def test_unknown_bounded_metric_cannot_pass(field):
    before = RunMetrics(success=False, hard_constraint_errors=1, tokens=10, latency_seconds=1)
    after = RunMetrics(success=True, hard_constraint_errors=0, tokens=10, latency_seconds=1)
    result = result_for(before, after.model_copy(update={field: None}))
    attribution = await OutcomeAttributor().analyze_improvement(result)
    assert (
        ValidationGate().decide(result, attribution, policy()).decision
        == GateDecision.CONTINUE_SAMPLING
    )


@pytest.mark.asyncio
async def test_zero_quality_gain_is_not_improvement():
    metrics = RunMetrics(
        quality=1, success=True, hard_constraint_errors=0, tokens=10, latency_seconds=1
    )
    result = result_for(metrics, metrics)
    attribution = await OutcomeAttributor().analyze_improvement(result)
    assert ValidationGate().decide(result, attribution, policy()).decision != GateDecision.PASS


@pytest.mark.asyncio
async def test_attribution_from_another_validation_cannot_authorize_pass():
    result = result_for(
        RunMetrics(success=False, hard_constraint_errors=1, tokens=10, latency_seconds=1),
        RunMetrics(success=True, hard_constraint_errors=0, tokens=10, latency_seconds=1),
    )
    attribution = await OutcomeAttributor().analyze_improvement(
        result.model_copy(update={"validation_id": "other"})
    )
    with pytest.raises(ValueError, match="归因"):
        ValidationGate().decide(result, attribution, policy())


@pytest.mark.asyncio
async def test_duplicate_or_shared_run_ids_are_not_paired_evidence():
    result = result_for(
        RunMetrics(success=False, hard_constraint_errors=1),
        RunMetrics(success=True, hard_constraint_errors=0),
    )
    result = result.model_copy(update={"candidate_run_ids": result.current_run_ids})
    attribution = await OutcomeAttributor().analyze_improvement(result)
    with pytest.raises(ValueError, match="配对"):
        ValidationGate().decide(result, attribution, policy())


@pytest.mark.asyncio
async def test_unregistered_or_insufficient_sample_count_cannot_pass():
    result = result_for(
        RunMetrics(success=False, hard_constraint_errors=1, tokens=10, latency_seconds=1),
        RunMetrics(success=True, hard_constraint_errors=0, tokens=10, latency_seconds=1),
    )
    attribution = await OutcomeAttributor().analyze_improvement(result)
    assert (
        ValidationGate()
        .decide(result, attribution, policy().model_copy(update={"minimum_paired_runs": None}))
        .decision
        == GateDecision.CONTINUE_SAMPLING
    )
