"""跨 Run 证据归纳与有状态监控；阈值仅为测试参数。"""

import pytest
from test_application import policy, sealed, serving

from evoteam.domain.evaluation import EvaluationIssue
from evoteam.domain.run import RunPurpose
from evoteam.experience.aggregator import ExperienceAggregator
from evoteam.monitoring.strategy_monitor import StrategyMonitor


def failed_run(strategy, run_id, *, error="resource_conflict"):
    run = sealed(strategy, run_id)
    return run.model_copy(
        update={
            "evaluation": run.evaluation.model_copy(
                update={
                    "issues": (
                        EvaluationIssue(
                            code=error,
                            message="fixture",
                            severity="error",
                            evidence_refs=("work:a", "work:b"),
                        ),
                    )
                }
            )
        }
    )


def test_aggregation_counts_runs_not_duplicate_issues_and_keeps_counterexamples():
    strategy = serving()
    first = failed_run(strategy, "r1")
    first = first.model_copy(
        update={
            "evaluation": first.evaluation.model_copy(
                update={"issues": first.evaluation.issues * 2}
            )
        }
    )
    second = failed_run(strategy, "r2")
    clean = sealed(strategy, "r3").model_copy(
        update={"evaluation": sealed(strategy, "r3").evaluation.model_copy(update={"issues": ()})}
    )
    patterns = ExperienceAggregator().aggregate((first, second, clean))
    assert len(patterns) == 1
    experience = patterns[0].failures[0]
    assert experience.supporting_runs == ("r1", "r2")
    assert experience.counterexample_runs == ()  # 无成功证据，不能把缺少错误当作成功反例。
    assert experience.confidence is None
    assert patterns[0].improvements == ()


def test_monitor_requires_enough_comparable_runs_and_repeated_same_error():
    strategy, rules = serving(), policy()
    first = failed_run(strategy, "r1")
    monitor = StrategyMonitor()
    assert monitor.inspect(strategy, (first,), rules).trigger is None
    assert (
        monitor.inspect(
            strategy, (first, failed_run(strategy, "r2", error="budget")), rules
        ).trigger
        is None
    )
    result = monitor.inspect(strategy, (first, failed_run(strategy, "r2")), rules)
    assert result.trigger is not None
    assert result.trigger.evidence_run_ids == ("r1", "r2")
    assert monitor.inspect(strategy, (first, failed_run(strategy, "r2")), rules) == result
    with pytest.raises(ValueError):
        monitor.inspect(
            strategy,
            (
                first,
                failed_run(strategy, "r2").model_copy(update={"purpose": RunPurpose.VALIDATION}),
            ),
            rules,
        )


@pytest.mark.asyncio
async def test_monitor_checkpoint_survives_reopen_and_respects_new_run_cooldown(tmp_path):
    from evoteam.monitoring.state import MonitorState
    from evoteam.storage.sqlite import SQLiteStorage

    strategy, rules = serving(), policy()
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'monitor.db'}")
    await storage.initialize()
    ports = await storage.open()
    assert ports.monitoring is not None
    monitor = StrategyMonitor()
    initial = MonitorState()
    window = (failed_run(strategy, "r1"), failed_run(strategy, "r2"))
    result, state = monitor.observe(strategy, window, rules, initial)
    assert result.trigger is not None
    await ports.monitoring.save("key", expected_revision=0, state=state)
    for pattern in ExperienceAggregator().aggregate(window):
        await ports.experiences.save_pattern(pattern)
        await ports.experiences.save_pattern(pattern)
    await storage.close()
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'monitor.db'}")
    ports = await storage.open()
    assert ports.monitoring is not None
    restored = await ports.monitoring.load("key")
    assert restored == state
    assert monitor.observe(strategy, window, rules, restored)[0] == result
    result, next_state = monitor.observe(
        strategy, (failed_run(strategy, "r2"), failed_run(strategy, "r3")), rules, restored
    )
    assert result.trigger is None
    result, next_state = monitor.observe(
        strategy, (failed_run(strategy, "r3"), failed_run(strategy, "r4")), rules, next_state
    )
    assert result.trigger is not None
    with pytest.raises(ValueError):
        await ports.monitoring.save("key", expected_revision=0, state=next_state)
    assert (
        len(
            await ports.experiences.list_patterns(
                strategy.metadata.ref, task_scope="project_planning"
            )
        )
        == 1
    )
    await storage.close()


def test_policy_cannot_change_under_the_same_version():
    from evoteam.monitoring.state import MonitorState

    strategy, rules = serving(), policy()
    window = (failed_run(strategy, "r1"), failed_run(strategy, "r2"))
    monitor = StrategyMonitor()
    _, state = monitor.observe(strategy, window, rules, MonitorState())
    changed = rules.model_copy(update={"cooldown_runs": rules.cooldown_runs + 1})
    with pytest.raises(ValueError, match="Policy"):
        monitor.observe(strategy, window, changed, state)


@pytest.mark.asyncio
async def test_growing_window_does_not_conflict_with_previously_saved_pattern(tmp_path):
    from evoteam.storage.sqlite import SQLiteStorage

    strategy = serving()
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'patterns.db'}")
    await storage.initialize()
    ports = await storage.open()
    aggregator = ExperienceAggregator()
    window = (failed_run(strategy, "r1"), failed_run(strategy, "r2"))
    first = aggregator.aggregate(window)[0]
    await ports.experiences.save_pattern(first)
    second = aggregator.aggregate((*window, failed_run(strategy, "r3", error="budget")))[0]
    await ports.experiences.save_pattern(second)
    assert second.supporting_runs == ("r1", "r2", "r3")
    assert (
        len(
            await ports.experiences.list_patterns(
                strategy.metadata.ref, task_scope="project_planning"
            )
        )
        == 2
    )
    await storage.close()
