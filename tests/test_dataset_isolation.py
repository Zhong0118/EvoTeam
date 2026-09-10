"""N2 dataset identity, partition isolation and pre-model rejection tests."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from evoteam.bootstrap import build_v0_strategy
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.dataset import (
    DatasetManifest,
    DatasetPartition,
    task_fingerprint,
    validate_partitions,
)
from evoteam.domain.evaluation import EvaluationResult, RunMetrics
from evoteam.domain.evolution import (
    EvolutionTrigger,
    TriggerType,
    ValidationPlan,
)
from evoteam.domain.planning import parse_planning_task
from evoteam.domain.run import RunPurpose, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task, TaskType
from evoteam.evolution.datasets import ManifestDatasets, ManifestHistoryValidator
from evoteam.evolution.manager import EvolutionManager
from evoteam.evolution.validator import Validator

MANIFEST = Path(__file__).parents[1] / "examples" / "datasets" / "project_planning_manifest.json"


def _task(task_id: str, *, instruction: str = "original", marker: str = "one") -> Task:
    return Task(
        task_id=task_id,
        task_type=TaskType.PROJECT_PLANNING,
        instruction=instruction,
        input_schema=AssetRef(id="project-planning-input", version="1"),
        inputs={"nested": {"b": 2, "a": 1}, "marker": marker},
    )


def _strategy(version: int, *, parent: StrategyRef | None = None) -> Strategy:
    data = build_v0_strategy(model_ref=AssetRef(id="fake", version="1")).model_dump()
    data["metadata"].update(
        {
            "ref": {"strategy_id": "project-planning", "version": version},
            "parent": parent.model_dump() if parent else None,
            "generation": version,
            "status": StrategyStatus.CURRENT if version == 0 else StrategyStatus.CANDIDATE,
        }
    )
    data["definition"]["orchestration"]["budget"] = {
        "max_tokens": 100,
        "max_tool_calls": 0,
        "timeout_seconds": 2,
    }
    for agent in data["definition"]["agents"]:
        agent["runtime_config"]["timeout_seconds"] = 1
    return Strategy.model_validate(data)


def _sealed(task: Task) -> SealedRun:
    return SealedRun(
        run_id=f"run-{task.task_id}",
        task_id=task.task_id,
        task_scope=task.task_type.value,
        strategy=StrategyRef(strategy_id="project-planning", version=0),
        purpose=RunPurpose.ONLINE,
        status=RunStatus.COMPLETED,
        sealed_at=datetime(2026, 1, 1, tzinfo=UTC),
        snapshot_ref=f"snapshot-{task.task_id}",
        trace_refs=(),
        evaluation=EvaluationResult(
            run_id=f"run-{task.task_id}",
            evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
            metrics=RunMetrics(success=False),
        ),
    )


def test_task_fingerprint_ignores_identity_instruction_and_json_key_order():
    task = _task("old-id", instruction="first wording")
    renamed = task.model_copy(update={"task_id": "new-id", "instruction": "new wording"}, deep=True)
    reordered = renamed.model_copy(
        update={"inputs": {"marker": "one", "nested": {"a": 1, "b": 2}}}, deep=True
    )

    assert task_fingerprint(task) == task_fingerprint(renamed) == task_fingerprint(reordered)
    assert task_fingerprint(task) != task_fingerprint(_task("other", marker="two"))


def test_validate_partitions_rejects_cross_partition_renames_and_invalid_shapes():
    task = _task("history")
    renamed = task.model_copy(update={"task_id": "validation", "instruction": "rewritten"})
    other = _task("final", marker="other")
    with pytest.raises(ValueError, match="跨分区"):
        validate_partitions({"history": [task], "validation": [renamed], "final_test": [other]})

    valid = {
        "history": [_task("history", marker="h")],
        "validation": [_task("validation", marker="v")],
        "final_test": [_task("final", marker="f")],
    }
    validate_partitions(valid)
    with pytest.raises(ValueError, match="不能为空"):
        validate_partitions({**valid, "validation": []})
    with pytest.raises(ValueError, match="Task ID"):
        validate_partitions({**valid, "validation": [_task("history", marker="v2")]})
    with pytest.raises(ValueError, match="分区键"):
        validate_partitions({"history": valid["history"], "validation": valid["validation"]})


def test_versioned_manifest_registers_all_subclasses_and_detects_content_change():
    manifest = DatasetManifest.model_validate_json(MANIFEST.read_text())
    datasets = ManifestDatasets(manifest)

    assert {dataset.partition for dataset in manifest.datasets} == set(DatasetPartition)
    assert {entry.subclass for dataset in manifest.datasets for entry in dataset.tasks} == {
        "resource_conflict",
        "dependency",
        "deadline",
        "skill",
        "budget",
        "valid_infeasible",
    }
    for dataset in manifest.datasets:
        tasks = datasets.load(dataset.ref, partition=dataset.partition)
        for task in tasks:
            parse_planning_task(task)
        assert tuple(task.task_id for task in tasks) == tuple(
            entry.task_id for entry in dataset.tasks
        )

    changed = json.loads(MANIFEST.read_text())
    changed["datasets"][0]["tasks"][0]["task"]["inputs"]["deadline_hour"] += 1
    with pytest.raises(ValueError, match="摘要"):
        DatasetManifest.model_validate(changed)


class _NoModelOrchestrator:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("dataset checks must run before model execution")


class _Unused:
    async def evaluate(self, *args, **kwargs):
        raise AssertionError("unused")

    def analyze(self, task):
        raise AssertionError("unused")

    async def seal_run(self, *args, **kwargs):
        raise AssertionError("unused")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dataset_ref",
    [
        AssetRef(id="unregistered", version="1"),
        AssetRef(id="project-planning-final-test", version="1"),
    ],
)
async def test_validator_rejects_unregistered_and_final_test_before_model_call(dataset_ref):
    datasets = ManifestDatasets(DatasetManifest.model_validate_json(MANIFEST.read_text()))
    orchestrator = _NoModelOrchestrator()
    unused = _Unused()
    validator = Validator(
        cast(Any, orchestrator),
        cast(Any, unused),
        cast(Any, unused),
        cast(Any, unused),
        datasets,
    )
    current = _strategy(0)
    candidate = _strategy(1, parent=current.metadata.ref)
    plan = ValidationPlan(
        dataset_ref=dataset_ref,
        evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
        repeats=1,
        seeds=(1,),
    )

    with pytest.raises((KeyError, ValueError)):
        await validator.validate(current, candidate, plan)
    assert orchestrator.calls == 0


class _SnapshotRuns:
    def __init__(self, snapshots) -> None:
        self.snapshots = snapshots

    async def read_snapshot(self, run_id):
        return self.snapshots[run_id]


@pytest.mark.asyncio
async def test_history_validator_resolves_manifest_and_rejects_renamed_or_changed_content():
    manifest = DatasetManifest.model_validate_json(MANIFEST.read_text())
    datasets = ManifestDatasets(manifest)
    history = next(dataset for dataset in manifest.datasets if dataset.partition == "history")
    entry = history.tasks[0]
    from evoteam.domain.run import RunResult, RunSnapshot

    strategy = _strategy(0)
    run = RunResult(
        run_id=f"run-{entry.task_id}",
        task_id=entry.task_id,
        strategy=strategy.metadata.ref,
        purpose=RunPurpose.ONLINE,
        status=RunStatus.COMPLETED,
    )
    snapshot = RunSnapshot(task=entry.task, strategy=strategy, run=run)
    sealed = _sealed(entry.task)
    validator = ManifestHistoryValidator(
        datasets, cast(Any, _SnapshotRuns({sealed.run_id: snapshot}))
    )

    sources = await validator.validate((sealed,))
    assert sources[0].manifest_ref == manifest.ref
    assert sources[0].dataset_ref == history.ref
    assert sources[0].task_fingerprint == entry.task_fingerprint

    for changed_task in (
        entry.task.model_copy(update={"task_id": "renamed"}, deep=True),
        entry.task.model_copy(
            update={"inputs": {**entry.task.inputs, "goal": "changed"}}, deep=True
        ),
    ):
        changed_run = run.model_copy(update={"task_id": changed_task.task_id}, deep=True)
        changed_snapshot = snapshot.model_copy(
            update={"task": changed_task, "run": changed_run}, deep=True
        )
        bad = ManifestHistoryValidator(
            datasets,
            cast(Any, _SnapshotRuns({sealed.run_id: changed_snapshot})),
        )
        with pytest.raises(ValueError, match="History"):
            await bad.validate((sealed,))


@pytest.mark.asyncio
async def test_manager_validates_only_history_before_claim_or_candidate_generation():
    class RejectHistory:
        def __init__(self) -> None:
            self.calls = 0

        async def validate(self, evidence):
            self.calls += 1
            raise ValueError("History 未登记")

    class Records:
        def __init__(self) -> None:
            self.claims = 0

        async def claim(self, *args):
            self.claims += 1
            return None

    history = RejectHistory()
    records = Records()
    manager = EvolutionManager(
        attributor=cast(Any, object()),
        generator=cast(Any, object()),
        validator=cast(Any, object()),
        gate=cast(Any, object()),
        lifecycle=cast(Any, object()),
        strategies=cast(Any, object()),
        records=cast(Any, records),
        history_validator=cast(Any, history),
    )
    current = _strategy(0)
    evidence = (_sealed(_task("unregistered")),)
    trigger = EvolutionTrigger(
        trigger_id="trigger",
        strategy=current.metadata.ref,
        policy_ref=AssetRef(id="policy", version="1"),
        trigger_type=TriggerType.REPEATED_FAILURE,
        task_scope="project_planning",
        evidence_run_ids=(evidence[0].run_id,),
        reason="fixture",
    )
    from evoteam.evolution.gate import GatePolicy
    from evoteam.monitoring.policy import EvolutionPolicy

    policy = EvolutionPolicy(
        ref=trigger.policy_ref,
        window_size=1,
        min_samples=1,
        repeated_failure_threshold=1,
        quality_drop_threshold=0.1,
        cost_overrun_threshold=0.1,
        low_contribution_threshold=0.1,
        cooldown_runs=1,
        max_candidates=1,
        stable_window_count=1,
    )
    plan = ValidationPlan(
        dataset_ref=AssetRef(id="project-planning-validation", version="1"),
        evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
        repeats=1,
        seeds=(1,),
    )
    gate = GatePolicy(
        ref=AssetRef(id="gate", version="1"),
        minimum_quality_gain=0,
        maximum_quality_regression=0,
        maximum_token_increase=0,
        maximum_latency_increase=0,
        minimum_paired_runs=2,
    )

    with pytest.raises(ValueError, match="History"):
        await manager.evolve(trigger, current, evidence, policy, plan, gate)
    assert history.calls == 1
    assert records.claims == 0
