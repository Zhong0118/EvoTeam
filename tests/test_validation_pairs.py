from evoteam.domain.evaluation import RunMetrics
from evoteam.domain.evolution import ValidationPair
from evoteam.evolution.validator import Validator


def _pair(fingerprint: str, repeat: int, success: bool, latency: float | None):
    metrics = RunMetrics(
        success=success,
        hard_constraint_errors=0 if success else 1,
        tokens=None,
        latency_seconds=latency,
    )
    return ValidationPair(
        task_id="task",
        task_fingerprint=fingerprint,
        subclass="deadline",
        repeat_index=repeat,
        current_run_id=f"c-{repeat}",
        candidate_run_id=f"n-{repeat}",
        current_metrics=metrics,
        candidate_metrics=metrics,
    )


def test_summary_counts_failed_runs_in_denominator_and_repeats_once():
    pairs = [_pair("same-task", 0, False, 3), _pair("same-task", 1, True, None)]
    summary = Validator._summary(pairs, candidate=False)
    aggregate = Validator._aggregate([pair.current_metrics for pair in pairs])
    assert summary.success_count == 1
    assert summary.total_count == 2
    assert summary.independent_task_count == 1
    assert summary.latency.sample_count == 1
    assert aggregate.tokens is None


def test_nearest_rank_p95_records_sample_size_without_stability_claim():
    distribution = Validator._latency([1, 2, 3, 4])
    assert distribution.algorithm == "nearest_rank"
    assert distribution.sample_count == 4
    assert distribution.p50_seconds == 2
    assert distribution.p95_seconds == 4
