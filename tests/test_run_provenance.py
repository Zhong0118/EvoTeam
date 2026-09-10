"""Execution-time dataset identity survives manifest replacement and reopening."""

from typing import Any, cast

import pytest
from test_online import ScriptedRuntime, configured_strategy

from evoteam.composition import build_application
from evoteam.domain.common import AssetRef
from evoteam.domain.dataset import DatasetPartition
from evoteam.domain.run import RunResult, RunSnapshot
from evoteam.evolution.datasets import (
    ManifestDatasets,
    ManifestHistoryValidator,
    PackagedValidationDatasets,
)
from evoteam.storage.sqlite import SQLiteStorage


@pytest.mark.asyncio
async def test_history_provenance_survives_manifest_replacement_and_database_reopen(tmp_path):
    datasets = PackagedValidationDatasets()
    history = next(item for item in datasets.manifest.datasets if item.partition == "history")
    task = history.tasks[0].task
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_strategy())
    app = build_application(runtime=ScriptedRuntime(), storage=ports)
    sealed = await app.tasks.execute(task, strategy_id="project-planning")
    await storage.close()

    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    ports = await storage.open()
    persisted = await ports.runs.get_sealed_run(sealed.run_id)
    replacement = ManifestDatasets(
        datasets.manifest.model_copy(
            update={"ref": AssetRef(id=datasets.manifest.ref.id, version="next-version")}
        )
    )
    sources = await ManifestHistoryValidator(replacement, ports.runs).validate((persisted,))
    assert sources[0].manifest_ref == datasets.manifest.ref
    assert sources[0].dataset_ref == history.ref
    assert persisted.dataset_source == sources[0]
    snapshot = await ports.runs.read_snapshot(sealed.run_id)
    assert snapshot.run.dataset_source == sources[0]
    await storage.close()


@pytest.mark.asyncio
async def test_legacy_history_without_provenance_is_readable_but_not_evolution_evidence():
    from test_dataset_isolation import _sealed, _SnapshotRuns, _strategy

    datasets = PackagedValidationDatasets()
    task = (
        next(item for item in datasets.manifest.datasets if item.partition == "history")
        .tasks[0]
        .task
    )
    sealed = _sealed(task)
    run = RunResult(
        run_id=sealed.run_id,
        task_id=task.task_id,
        strategy=sealed.strategy,
        purpose=sealed.purpose,
        status=sealed.status,
    )
    snapshot = RunSnapshot(task=task, strategy=_strategy(0), run=run)
    validator = ManifestHistoryValidator(
        datasets, cast(Any, _SnapshotRuns({sealed.run_id: snapshot}))
    )
    with pytest.raises(ValueError, match="来源|provenance"):
        await validator.validate((sealed,))


@pytest.mark.asyncio
async def test_explicit_wrong_source_rejected_before_runtime(tmp_path):
    datasets = PackagedValidationDatasets()
    history = next(item for item in datasets.manifest.datasets if item.partition == "history")
    task = history.tasks[0].task
    source = datasets.source_for(history.tasks[1].task, partition=DatasetPartition.HISTORY)
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_strategy())
    runtime = ScriptedRuntime()
    app = build_application(runtime=runtime, storage=ports)
    with pytest.raises(ValueError, match="来源|source"):
        await app.tasks.execute(task, strategy_id="project-planning", dataset_source=source)
    assert runtime.messages == []
    await storage.close()


@pytest.mark.asyncio
async def test_store_rejects_sealed_snapshot_source_mismatch(tmp_path):
    from sqlalchemy import update

    from evoteam.storage.sqlite import runs

    datasets = PackagedValidationDatasets()
    task = (
        next(item for item in datasets.manifest.datasets if item.partition == "history")
        .tasks[0]
        .task
    )
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_strategy())
    app = build_application(runtime=ScriptedRuntime(), storage=ports)
    sealed = await app.tasks.execute(task, strategy_id="project-planning")
    altered = sealed.model_copy(update={"dataset_source": None})
    assert storage._engine is not None
    with storage._engine.begin() as conn:
        conn.execute(
            update(runs)
            .where(runs.c.run_id == sealed.run_id)
            .values(sealed=altered.model_dump_json())
        )
    with pytest.raises(ValueError, match="来源|source"):
        await ports.runs.read_snapshot(sealed.run_id)
    await storage.close()


@pytest.mark.asyncio
async def test_validation_runs_seal_original_partition_source(tmp_path):
    from test_dataset_isolation import _strategy

    from evoteam.composition import StoreEventSink
    from evoteam.domain.evolution import ValidationPlan
    from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
    from evoteam.evolution.validator import Validator
    from evoteam.orchestration.orchestrator import Orchestrator
    from evoteam.orchestration.task_analyzer import TaskAnalyzer

    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    await storage.initialize()
    ports = await storage.open()
    current = _strategy(0)
    candidate = _strategy(1, parent=current.metadata.ref)
    await ports.strategies.save(current)
    await ports.strategies.save(candidate)
    datasets = PackagedValidationDatasets()
    validation = next(item for item in datasets.manifest.datasets if item.partition == "validation")
    validator = Validator(
        Orchestrator(ScriptedRuntime(), StoreEventSink(ports.runs)),
        ProjectPlanningEvaluator(),
        TaskAnalyzer(),
        ports.runs,
        datasets,
    )
    result = await validator.validate(
        current,
        candidate,
        ValidationPlan(
            dataset_ref=validation.ref,
            evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
            repeats=1,
            seeds=(1,),
        ),
    )
    for run_id in (*result.current_run_ids, *result.candidate_run_ids):
        sealed = await ports.runs.get_sealed_run(run_id)
        assert sealed.dataset_source is not None
        assert sealed.dataset_source.partition == DatasetPartition.VALIDATION
        assert sealed.dataset_source.dataset_ref == validation.ref
        snapshot = await ports.runs.read_snapshot(run_id)
        assert snapshot.run.dataset_source == sealed.dataset_source
        with pytest.raises(ValueError, match="online"):
            await ManifestHistoryValidator(datasets, ports.runs).validate((sealed,))
    await storage.close()
