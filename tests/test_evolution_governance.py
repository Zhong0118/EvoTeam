"""治理重试、并发消费和取消必须在真实 SQLite 边界收敛。"""

import asyncio
import json
from pathlib import Path

import pytest
from test_evolution import (
    EXAMPLE,
    FixedEvidenceAttributor,
    PromptSensitiveRuntime,
    configured_current,
    failure_evidence,
)

from evoteam.composition import StoreEventSink
from evoteam.domain.common import AssetRef
from evoteam.domain.evolution import EvolutionTrigger, TriggerType, ValidationPlan
from evoteam.domain.run import RunPurpose, RunStatus
from evoteam.domain.strategy import StrategyStatus
from evoteam.domain.task import Task
from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
from evoteam.evolution.datasets import InMemoryValidationDatasets
from evoteam.evolution.gate import GatePolicy, ValidationGate
from evoteam.evolution.lifecycle import StrategyLifecycle
from evoteam.evolution.manager import EvolutionManager
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import Validator
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.storage.sqlite import SQLiteStorage


class FixtureHistoryValidator:
    async def validate(self, evidence):
        return ()


@pytest.fixture
async def governance(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'governance.db'}")
    await storage.initialize()
    ports = await storage.open()
    current = configured_current()
    await ports.strategies.save(current)
    policy = EvolutionPolicy.model_validate_json(
        (Path(__file__).parents[1] / "examples/monitor_policy.example.json").read_text()
    )
    evidence = failure_evidence(current)
    trigger = EvolutionTrigger(
        trigger_id="governance-trigger",
        strategy=current.metadata.ref,
        policy_ref=policy.ref,
        trigger_type=TriggerType.REPEATED_FAILURE,
        task_scope="project_planning",
        evidence_run_ids=tuple(r.run_id for r in evidence),
        reason="重复资源冲突",
    )
    plan = ValidationPlan(
        dataset_ref=AssetRef(id="held-out", version="1"),
        evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
        repeats=1,
        seeds=(7,),
    )
    gate = GatePolicy(
        ref=AssetRef(id="strict", version="1"),
        minimum_quality_gain=1,
        maximum_quality_regression=0,
        maximum_token_increase=0,
        maximum_latency_increase=0,
    )
    task = Task.model_validate_json((EXAMPLE / "task.json").read_text())

    def manager(runtime):
        validator = Validator(
            Orchestrator(runtime, StoreEventSink(ports.runs)),
            ProjectPlanningEvaluator(),
            TaskAnalyzer(),
            ports.runs,
            InMemoryValidationDatasets({("held-out", "1"): (task,)}),
        )
        return EvolutionManager(
            FixedEvidenceAttributor(),
            CandidateGenerator(),
            validator,
            ValidationGate(),
            StrategyLifecycle(ports.strategies),
            ports.strategies,
            ports.evolutions,
            FixtureHistoryValidator(),
        )

    yield storage, ports, manager, (trigger, current, evidence, policy, plan, gate)
    await storage.close()


class RejectingRuntime(PromptSensitiveRuntime):
    async def invoke(self, agent, message, context):
        result = await super().invoke(agent, message, context)
        if agent.node_id == "executor":
            return result.model_copy(
                update={"output": json.loads((EXAMPLE / "plan.json").read_text())}
            )
        return result


@pytest.mark.asyncio
async def test_repeated_trigger_returns_record_without_revalidation(governance):
    _, ports, make, args = governance
    runtime = RejectingRuntime()
    manager = make(runtime)
    first = await manager.evolve(*args)
    assert first.promoted is None
    calls = len(runtime.messages)
    second = await manager.evolve(*args)
    assert second == first
    assert len(runtime.messages) == calls
    assert (await ports.strategies.allocate_version(args[1].metadata.ref.strategy_id)).version == 2


@pytest.mark.asyncio
async def test_concurrent_trigger_does_not_start_second_validation(governance):
    _, _, make, args = governance
    entered, release = asyncio.Event(), asyncio.Event()

    class PausedRuntime(RejectingRuntime):
        async def invoke(self, agent, message, context):
            entered.set()
            await release.wait()
            return await super().invoke(agent, message, context)

    first_runtime = PausedRuntime()
    first_task = asyncio.create_task(make(first_runtime).evolve(*args))
    await asyncio.wait_for(entered.wait(), timeout=5)
    second_runtime = RejectingRuntime()
    try:
        with pytest.raises(ValueError, match="进行中"):
            await make(second_runtime).evolve(*args)
        assert not second_runtime.messages
    finally:
        release.set()
        await first_task


@pytest.mark.asyncio
async def test_cancelled_validation_seals_run_and_stops_all_following_calls(governance):
    _, ports, make, args = governance
    entered = asyncio.Event()

    class BlockingRuntime(RejectingRuntime):
        calls = 0

        async def invoke(self, agent, message, context):
            self.calls += 1
            if self.calls == 1:
                entered.set()
                await asyncio.Event().wait()
            return await super().invoke(agent, message, context)

    runtime = BlockingRuntime()
    manager = make(runtime)
    running = asyncio.create_task(manager.evolve(*args))
    await asyncio.wait_for(entered.wait(), timeout=5)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert runtime.calls == 1
    runs = await ports.runs.recent_runs(
        args[1].metadata.ref, task_scope="project_planning", purpose=RunPurpose.VALIDATION, limit=10
    )
    assert len(runs) == 1 and runs[0].status == RunStatus.CANCELLED
    record = await manager.evolve(*args)
    assert record.termination_reason == "cancelled"
    assert record.promoted is None
    for ref in record.candidates:
        assert (await ports.strategies.get(ref)).metadata.status == StrategyStatus.REJECTED
    assert runtime.calls == 1


@pytest.mark.asyncio
async def test_strategy_lookup_uses_domain_missing_resource_error(governance):
    _, ports, _, args = governance
    with pytest.raises(KeyError):
        await ports.strategies.current("missing")
    with pytest.raises(KeyError):
        await ports.strategies.get(args[1].metadata.ref.model_copy(update={"version": 999}))


@pytest.mark.asyncio
async def test_consumed_trigger_cannot_change_registered_validation_settings(governance):
    _, _, make, args = governance
    runtime = RejectingRuntime()
    manager = make(runtime)
    await manager.evolve(*args)
    calls = len(runtime.messages)
    changed = (*args[:4], args[4].model_copy(update={"seeds": (8,)}), args[5])
    with pytest.raises(ValueError, match="配置不能更改"):
        await manager.evolve(*changed)
    assert len(runtime.messages) == calls


@pytest.mark.asyncio
async def test_stale_evolution_aborts_without_overwriting_new_current(governance):
    from evoteam.domain.evolution import EvolutionRecord
    from evoteam.experience.evidence import evidence_id

    _, ports, make, args = governance
    manager = make(RejectingRuntime())
    original = manager.validator
    newer_ref = None

    class ChangingValidator:
        async def validate(self, current, candidate, plan):
            nonlocal newer_ref
            result = await original.validate(current, candidate, plan)
            newer_ref = await ports.strategies.allocate_version(current.metadata.ref.strategy_id)
            successor = candidate.model_copy(
                update={
                    "metadata": candidate.metadata.model_copy(
                        update={"ref": newer_ref, "status": StrategyStatus.CANDIDATE}
                    )
                }
            )
            await ports.strategies.save(successor)
            await ports.strategies.apply_lifecycle(
                expected_current=current.metadata.ref,
                updated_versions=(
                    current.model_copy(
                        update={
                            "metadata": current.metadata.model_copy(
                                update={"status": StrategyStatus.RETIRED}
                            )
                        }
                    ),
                    successor.model_copy(
                        update={
                            "metadata": successor.metadata.model_copy(
                                update={"status": StrategyStatus.CURRENT}
                            )
                        }
                    ),
                ),
                serving=newer_ref,
                record=EvolutionRecord(
                    evolution_id="other-governance", trigger=args[0], promoted=newer_ref
                ),
            )
            return result

    manager.validator = ChangingValidator()
    with pytest.raises(ValueError):
        await manager.evolve(*args)
    evolution_id = evidence_id("evolution", [args[0].trigger_id, args[1].metadata.ref.model_dump()])
    record = await ports.evolutions.get_record(evolution_id)
    assert record.termination_reason == "ValueError"
    assert (
        await ports.strategies.current(args[1].metadata.ref.strategy_id)
    ).metadata.ref == newer_ref
    for ref in record.candidates:
        assert (await ports.strategies.get(ref)).metadata.status == StrategyStatus.REJECTED


@pytest.mark.asyncio
async def test_claim_survives_reopen_and_excludes_other_trigger_on_same_strategy(
    governance, tmp_path
):
    from evoteam.domain.evolution import EvolutionRecord

    _, ports, _, args = governance
    strategy = args[1].metadata.ref
    assert await ports.evolutions.claim("claim-one", strategy, "fingerprint") is None
    second = SQLiteStorage(f"sqlite:///{tmp_path / 'governance.db'}")
    try:
        other = await second.open()
        with pytest.raises(ValueError, match="进行中"):
            await other.evolutions.claim("claim-one", strategy, "fingerprint")
        with pytest.raises(ValueError, match="进行中"):
            await other.evolutions.claim("claim-two", strategy, "other-fingerprint")
        record = EvolutionRecord(evolution_id="claim-one", trigger=args[0])
        await ports.evolutions.save_record(record)
        assert await other.evolutions.claim("claim-one", strategy, "fingerprint") == record
        assert await other.evolutions.claim("claim-two", strategy, "other-fingerprint") is None
    finally:
        await second.close()
