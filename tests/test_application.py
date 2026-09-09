"""使用记录调用的替身验证模块关联；不把假数据当作业务实验结果。"""

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from evoteam.application import EvolutionService, TaskService
from evoteam.bootstrap import build_v0_strategy
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.evaluation import EvaluationResult, RunMetrics
from evoteam.domain.evolution import (
    EvolutionRecord,
    EvolutionTrigger,
    MonitorResult,
    TriggerType,
    ValidationPlan,
)
from evoteam.domain.experience import OutcomePattern
from evoteam.domain.run import RunPurpose, RunResult, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task, TaskProfile, TaskType
from evoteam.evolution.gate import GatePolicy
from evoteam.monitoring.policy import EvolutionPolicy


def serving(status: StrategyStatus = StrategyStatus.CURRENT) -> Strategy:
    draft = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1"))
    return draft.model_copy(
        update={"metadata": draft.metadata.model_copy(update={"status": status})}
    )


def policy() -> EvolutionPolicy:
    # 仅供测试流程分支，不是项目选定的演进阈值。
    return EvolutionPolicy(
        ref=AssetRef(id="test-policy", version="1"),
        window_size=2,
        min_samples=2,
        repeated_failure_threshold=2,
        quality_drop_threshold=0.1,
        cost_overrun_threshold=0.2,
        low_contribution_threshold=0.01,
        cooldown_runs=2,
        max_candidates=1,
        stable_window_count=2,
    )


def task() -> Task:
    return Task(
        task_id="t1",
        task_type=TaskType.PROJECT_PLANNING,
        instruction="测试任务",
        input_schema=AssetRef(id="fixture-task", version="1"),
    )


def sealed(
    strategy: Strategy, run_id: str = "history-1", purpose: RunPurpose = RunPurpose.ONLINE
) -> SealedRun:
    return SealedRun(
        run_id=run_id,
        task_id="t1",
        task_scope="project_planning",
        strategy=strategy.metadata.ref,
        purpose=purpose,
        status=RunStatus.FAILED,
        sealed_at=datetime.now(UTC),
        snapshot_ref=f"fixture:{run_id}",
        trace_refs=(),
        evaluation=EvaluationResult(
            run_id=run_id,
            evaluator_ref=AssetRef(id="fixture", version="1"),
            metrics=RunMetrics(success=False),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.CANCELLED]
)
async def test_task_orders_execute_evaluate_and_atomic_archive(status: RunStatus):
    calls: list[str] = []
    strategy = serving()
    strategies = Mock()

    async def current(_):
        calls.append("current")
        return strategy

    strategies.current = AsyncMock(side_effect=current)
    analyzer = Mock()

    def analyze(value):
        calls.append("analyze")
        return TaskProfile(task_id=value.task_id, task_type=value.task_type)

    analyzer.analyze.side_effect = analyze
    orchestrator = Mock()

    async def execute(value, profile, selected, *, run_id, purpose):
        calls.append("execute")
        assert selected is strategy
        assert purpose == RunPurpose.ONLINE
        return RunResult(
            run_id=run_id,
            task_id=value.task_id,
            strategy=selected.metadata.ref,
            purpose=purpose,
            status=status,
        )

    orchestrator.execute = AsyncMock(side_effect=execute)
    evaluator = Mock()

    async def evaluate(value, run):
        calls.append("evaluate")
        return EvaluationResult(
            run_id=run.run_id,
            evaluator_ref=AssetRef(id="fixture", version="1"),
            metrics=RunMetrics(success=status == RunStatus.COMPLETED),
        )

    evaluator.evaluate = AsyncMock(side_effect=evaluate)
    runs = Mock()

    async def seal_run(value, run, evaluation, *, task_scope):
        calls.append("seal")
        return SealedRun(
            run_id=run.run_id,
            task_id=run.task_id,
            task_scope=task_scope,
            strategy=run.strategy,
            purpose=run.purpose,
            status=run.status,
            sealed_at=datetime.now(UTC),
            snapshot_ref="fixture:snapshot",
            trace_refs=(),
            evaluation=evaluation,
        )

    runs.seal_run = AsyncMock(side_effect=seal_run)
    service = TaskService(analyzer, orchestrator, evaluator, runs, strategies)
    result = await service.execute(task(), strategy_id="project-planning")
    assert calls == ["current", "analyze", "execute", "evaluate", "seal"]
    assert result.status == status
    assert result.task_scope == "project_planning"
    assert result.run_id
    # TaskService 没有 Monitor/Manager 依赖，不会每个任务都发起演进。
    assert not hasattr(service, "manager")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [StrategyStatus.DRAFT, StrategyStatus.CANDIDATE, StrategyStatus.REJECTED]
)
async def test_online_rejects_unserved_strategy_before_running(status: StrategyStatus):
    strategies = Mock(current=AsyncMock(return_value=serving(status)))
    orchestrator = Mock(execute=AsyncMock())
    service = TaskService(Mock(), orchestrator, Mock(), Mock(), strategies)
    with pytest.raises(ValueError, match="CURRENT|STABLE"):
        await service.execute(task(), strategy_id="project-planning")
    orchestrator.execute.assert_not_awaited()


def observation_fixture(triggered: bool = False):
    strategy = serving(StrategyStatus.STABLE)
    evidence = (sealed(strategy), sealed(strategy, "history-2"))
    rules = policy()
    trigger = (
        EvolutionTrigger(
            trigger_id="trigger-1",
            strategy=strategy.metadata.ref,
            policy_ref=rules.ref,
            trigger_type=TriggerType.REPEATED_FAILURE,
            task_scope="project_planning",
            evidence_run_ids=tuple(run.run_id for run in evidence),
            reason="fixture signal",
        )
        if triggered
        else None
    )
    result = MonitorResult(
        strategy=strategy.metadata.ref, sample_count=2, reason="fixture", trigger=trigger
    )
    strategies = Mock(current=AsyncMock(return_value=strategy))
    runs = Mock(recent_runs=AsyncMock(return_value=evidence))
    experiences = Mock(save_pattern=AsyncMock())
    aggregator = Mock(aggregate=Mock(return_value=()))
    monitor = Mock(inspect=Mock(return_value=result))
    manager = Mock(
        evolve=AsyncMock(
            return_value=EvolutionRecord(
                evolution_id="e1",
                trigger=trigger,
            )
            if trigger
            else None
        )
    )
    service = EvolutionService(strategies, runs, experiences, aggregator, monitor, manager)
    return service, strategy, evidence, rules, result, manager


def validation_plan() -> ValidationPlan:
    return ValidationPlan(
        dataset_ref=AssetRef(id="held-out", version="1"),
        evaluator_ref=AssetRef(id="fixture", version="1"),
        repeats=1,
        seeds=(1,),
    )


@pytest.mark.asyncio
async def test_inspection_persists_patterns_before_monitoring():
    service, strategy, evidence, rules, result, _ = observation_fixture()
    calls: list[str] = []
    pattern = OutcomePattern(
        pattern_id="pattern-1",
        strategy=strategy.metadata.ref,
        task_scope="project_planning",
        supporting_runs=tuple(run.run_id for run in evidence),
    )

    def aggregate(runs):
        assert runs == evidence
        calls.append("aggregate")
        return (pattern,)

    async def save_pattern(value):
        assert value is pattern
        calls.append("save_pattern")

    def inspect(selected, runs, selected_policy):
        assert selected is strategy
        assert runs == evidence
        assert selected_policy is rules
        calls.append("monitor")
        return result

    cast(Mock, service.aggregator.aggregate).side_effect = aggregate
    cast(AsyncMock, service.experiences.save_pattern).side_effect = save_pattern
    cast(Mock, service.monitor.inspect).side_effect = inspect
    observation = await service.inspect(
        strategy_id="project-planning", task_scope="project_planning", policy=rules
    )
    assert calls == ["aggregate", "save_pattern", "monitor"]
    assert observation.runs == evidence


def gate_policy() -> GatePolicy:
    return GatePolicy(
        ref=AssetRef(id="test-gate", version="1"),
        minimum_quality_gain=0.1,
        maximum_quality_regression=0,
        maximum_token_increase=0.1,
        maximum_latency_increase=0.1,
    )


@pytest.mark.asyncio
async def test_stable_without_trigger_never_dispatches_evolution():
    service, strategy, evidence, rules, result, manager = observation_fixture()
    record = await service.evolve_if_needed(
        strategy_id="project-planning",
        task_scope="project_planning",
        policy=rules,
        validation_plan=validation_plan(),
        gate_policy=gate_policy(),
    )
    assert record is None
    manager.evolve.assert_not_awaited()
    cast(AsyncMock, service.runs.recent_runs).assert_awaited_once_with(
        strategy.metadata.ref,
        task_scope="project_planning",
        purpose=RunPurpose.ONLINE,
        limit=rules.window_size,
    )


@pytest.mark.asyncio
async def test_trigger_passes_exact_observed_evidence_to_manager():
    service, strategy, evidence, rules, result, manager = observation_fixture(True)
    plan, gate = validation_plan(), gate_policy()
    record = await service.evolve_if_needed(
        strategy_id="project-planning",
        task_scope="project_planning",
        policy=rules,
        validation_plan=plan,
        gate_policy=gate,
    )
    manager.evolve.assert_awaited_once_with(result.trigger, strategy, evidence, rules, plan, gate)
    assert record is not None
    assert record.evolution_id == "e1"
    # 再读 Current 可以检测陈旧触发，但不能重读一个已变化的历史窗口。
    cast(AsyncMock, service.runs.recent_runs).assert_awaited_once()


@pytest.mark.asyncio
async def test_validation_runs_cannot_enter_online_monitor_even_if_store_returns_them():
    service, strategy, evidence, rules, result, manager = observation_fixture(True)
    cast(AsyncMock, service.runs.recent_runs).return_value = (
        sealed(strategy, purpose=RunPurpose.VALIDATION),
    )
    with pytest.raises(ValueError, match="online|线上"):
        await service.evolve_if_needed(
            strategy_id="project-planning",
            task_scope="project_planning",
            policy=rules,
            validation_plan=validation_plan(),
            gate_policy=gate_policy(),
        )
    cast(Mock, service.monitor.inspect).assert_not_called()
    manager.evolve.assert_not_awaited()


@pytest.mark.asyncio
async def test_strategy_change_during_observation_prevents_stale_dispatch():
    service, strategy, evidence, rules, result, manager = observation_fixture(True)
    newer = strategy.model_copy(
        update={
            "metadata": strategy.metadata.model_copy(
                update={
                    "ref": StrategyRef(strategy_id="project-planning", version=1),
                }
            )
        }
    )
    cast(AsyncMock, service.strategies.current).side_effect = [strategy, newer]
    with pytest.raises(ValueError, match="变更|changed"):
        await service.evolve_if_needed(
            strategy_id="project-planning",
            task_scope="project_planning",
            policy=rules,
            validation_plan=validation_plan(),
            gate_policy=gate_policy(),
        )
    manager.evolve.assert_not_awaited()


@pytest.mark.asyncio
async def test_composition_shares_execution_and_evaluation_without_starting_io():
    from evoteam.composition import build_application
    from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
    from evoteam.storage.sqlite import StoragePorts

    calls = Mock()
    stores = StoragePorts(runs=calls, strategies=calls, experiences=calls, evolutions=calls)
    runtime = OpenJiuwenRuntimeAdapter()
    app = build_application(runtime=runtime, storage=stores)
    assert app.tasks.orchestrator is app.evolution.manager.validator.orchestrator
    assert app.tasks.evaluator is app.evolution.manager.validator.evaluator
    assert app.tasks.orchestrator.runtime is runtime
    assert calls.mock_calls == []


@pytest.mark.asyncio
async def test_evaluation_failure_does_not_create_fake_archive():
    service_task = task()
    strategy = serving()
    analyzer = Mock(
        analyze=Mock(
            return_value=TaskProfile(
                task_id=service_task.task_id,
                task_type=service_task.task_type,
            )
        )
    )

    async def execute(value, profile, selected, *, run_id, purpose):
        return RunResult(
            run_id=run_id,
            task_id=value.task_id,
            strategy=selected.metadata.ref,
            purpose=purpose,
            status=RunStatus.COMPLETED,
        )

    orchestrator = Mock(execute=AsyncMock(side_effect=execute))
    evaluator = Mock(evaluate=AsyncMock(side_effect=RuntimeError("judge unavailable")))
    runs = Mock(seal_run=AsyncMock())
    service = TaskService(
        analyzer, orchestrator, evaluator, runs, Mock(current=AsyncMock(return_value=strategy))
    )
    with pytest.raises(RuntimeError, match="judge unavailable"):
        await service.execute(service_task, strategy_id="project-planning")
    runs.seal_run.assert_not_awaited()
