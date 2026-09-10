"""A0 read-query contract tests for the core persistence ports."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from evoteam.bootstrap import build_v0_strategy
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.evaluation import EvaluationResult, RunMetrics
from evoteam.domain.evolution import EvolutionRecord, EvolutionTrigger, TriggerType
from evoteam.domain.run import RunPurpose, RunResult, RunSnapshot, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task, TaskType
from evoteam.runtime.models import ModelEndpoint
from evoteam.storage.sqlite import SQLiteStorage, evolutions, metadata, runs


def _strategy(strategy_id: str, version: int) -> Strategy:
    value = build_v0_strategy(model_ref=AssetRef(id="fake", version="1")).model_dump()
    value["metadata"].update(
        {
            "ref": {"strategy_id": strategy_id, "version": version},
            "generation": version,
            "status": StrategyStatus.DRAFT,
        }
    )
    return Strategy.model_validate(value)


def _sealed_run(
    strategy: Strategy,
    run_id: str,
    purpose: RunPurpose,
    sealed_at: datetime,
) -> tuple[SealedRun, RunSnapshot]:
    task = Task(
        task_id=f"task-{run_id}",
        task_type=TaskType.PROJECT_PLANNING,
        instruction="plan",
        input_schema=AssetRef(id="planning-task", version="1"),
    )
    result = RunResult(
        run_id=run_id,
        task_id=task.task_id,
        strategy=strategy.metadata.ref,
        purpose=purpose,
        status=RunStatus.COMPLETED,
    )
    sealed = SealedRun(
        run_id=run_id,
        task_id=task.task_id,
        task_scope=task.task_type.value,
        strategy=strategy.metadata.ref,
        purpose=purpose,
        status=result.status,
        sealed_at=sealed_at,
        snapshot_ref=f"sqlite:run:{run_id}",
        trace_refs=(),
        evaluation=EvaluationResult(
            run_id=run_id,
            evaluator_ref=AssetRef(id="rules", version="1"),
            metrics=RunMetrics(success=True),
        ),
    )
    return sealed, RunSnapshot(task=task, strategy=strategy, run=result)


def _insert_run(storage: SQLiteStorage, sealed: SealedRun, snapshot: RunSnapshot) -> None:
    with storage._connect().begin() as connection:
        connection.execute(
            runs.insert().values(
                run_id=sealed.run_id,
                strategy_id=sealed.strategy.strategy_id,
                version=sealed.strategy.version,
                scope=sealed.task_scope,
                purpose=sealed.purpose.value,
                sealed_at=sealed.sealed_at.isoformat(),
                snapshot=snapshot.model_dump_json(),
                sealed=sealed.model_dump_json(),
            )
        )


def _record(strategy_id: str, evolution_id: str) -> EvolutionRecord:
    return EvolutionRecord(
        evolution_id=evolution_id,
        trigger=EvolutionTrigger(
            trigger_id=f"trigger-{evolution_id}",
            strategy=StrategyRef(strategy_id=strategy_id, version=0),
            policy_ref=AssetRef(id="policy", version="1"),
            trigger_type=TriggerType.REPEATED_FAILURE,
            task_scope="project_planning",
            evidence_run_ids=("evidence",),
            reason="fixture",
        ),
    )


async def _storage(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'read-queries.db'}")
    await storage.initialize()
    return storage, await storage.open()


@pytest.mark.asyncio
async def test_empty_lists_and_missing_single_records_raise_key_error(tmp_path):
    storage, ports = await _storage(tmp_path)

    assert await ports.runs.list_runs("missing", purpose=None, limit=10, cursor=None) == ((), None)
    assert await ports.strategies.list_versions("missing") == ()
    assert await ports.evolutions.list_records("missing", limit=10, cursor=None) == ((), None)

    missing_reads = (
        ports.runs.get_sealed_run("missing"),
        ports.runs.read_snapshot("missing"),
        ports.evolutions.get_record("missing"),
        ports.evolutions.get_attribution("missing"),
        ports.evolutions.get_proposal("missing"),
        ports.evolutions.get_validation("missing"),
    )
    for read in missing_reads:
        with pytest.raises(KeyError):
            await read
    assert await ports.runs.events_for_run("missing") == ()
    await storage.close()


@pytest.mark.asyncio
async def test_list_versions_isolated_and_sorted_ascending(tmp_path):
    storage, ports = await _storage(tmp_path)
    for version in (2, 0, 1):
        await ports.strategies.save(_strategy("alpha", version))
    await ports.strategies.save(_strategy("beta", 7))

    versions = await ports.strategies.list_versions("alpha")

    assert tuple(item.metadata.ref.version for item in versions) == (0, 1, 2)
    assert all(item.metadata.ref.strategy_id == "alpha" for item in versions)
    await storage.close()


@pytest.mark.asyncio
async def test_list_runs_filters_and_uses_stable_filter_bound_cursor(tmp_path):
    storage, ports = await _storage(tmp_path)
    alpha = _strategy("alpha", 0)
    beta = _strategy("beta", 0)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    fixtures = (
        (alpha, "run-a", RunPurpose.ONLINE, base + timedelta(minutes=3)),
        (alpha, "run-b", RunPurpose.ONLINE, base + timedelta(minutes=2)),
        (alpha, "run-c", RunPurpose.ONLINE, base + timedelta(minutes=2)),
        (alpha, "run-d", RunPurpose.ONLINE, base + timedelta(minutes=1)),
        (alpha, "validation", RunPurpose.VALIDATION, base + timedelta(minutes=4)),
        (beta, "other-strategy", RunPurpose.ONLINE, base + timedelta(minutes=5)),
    )
    for fixture in fixtures:
        sealed, snapshot = _sealed_run(*fixture)
        _insert_run(storage, sealed, snapshot)

    first, cursor = await ports.runs.list_runs(
        "alpha", purpose=RunPurpose.ONLINE, limit=2, cursor=None
    )
    assert tuple(item.run_id for item in first) == ("run-a", "run-b")
    assert cursor is not None

    # A newer row inserted between pages must not shift or duplicate the remaining page.
    sealed, snapshot = _sealed_run(
        alpha, "run-new", RunPurpose.ONLINE, base + timedelta(minutes=10)
    )
    _insert_run(storage, sealed, snapshot)
    second, final_cursor = await ports.runs.list_runs(
        "alpha", purpose=RunPurpose.ONLINE, limit=2, cursor=cursor
    )
    assert tuple(item.run_id for item in second) == ("run-c", "run-d")
    assert final_cursor is None

    all_purposes, _ = await ports.runs.list_runs("alpha", purpose=None, limit=20, cursor=None)
    assert {item.run_id for item in all_purposes} == {
        "run-new",
        "run-a",
        "run-b",
        "run-c",
        "run-d",
        "validation",
    }
    assert await ports.runs.events_for_run("run-a") == ()
    assert (await ports.runs.get_sealed_run("run-a")).run_id == "run-a"

    with pytest.raises(ValueError):
        await ports.runs.list_runs("alpha", purpose=RunPurpose.VALIDATION, limit=2, cursor=cursor)
    with pytest.raises(ValueError):
        await ports.runs.list_runs("beta", purpose=RunPurpose.ONLINE, limit=2, cursor=cursor)
    for invalid_limit in (0, -1, 101):
        with pytest.raises(ValueError):
            await ports.runs.list_runs(
                "alpha", purpose=RunPurpose.ONLINE, limit=invalid_limit, cursor=None
            )
    with pytest.raises(ValueError):
        await ports.runs.list_runs("alpha", purpose=None, limit=2, cursor="not-a-cursor")
    await storage.close()


@pytest.mark.asyncio
async def test_list_evolution_records_isolated_and_cursor_bound(tmp_path):
    storage, ports = await _storage(tmp_path)
    strategy = _strategy("alpha", 0)
    for index in range(2):
        sealed, snapshot = _sealed_run(
            strategy,
            f"run-{index}",
            RunPurpose.ONLINE,
            datetime(2026, 1, index + 1, tzinfo=UTC),
        )
        _insert_run(storage, sealed, snapshot)
    for evolution_id in ("evo-c", "evo-a", "evo-b"):
        await ports.evolutions.save_record(_record("alpha", evolution_id))
    await ports.evolutions.save_record(_record("beta", "evo-beta"))

    first, cursor = await ports.evolutions.list_records("alpha", limit=2, cursor=None)
    second, final_cursor = await ports.evolutions.list_records("alpha", limit=2, cursor=cursor)
    assert tuple(item.evolution_id for item in first) == ("evo-a", "evo-b")
    assert tuple(item.evolution_id for item in second) == ("evo-c",)
    assert final_cursor is None
    assert cursor is not None

    with pytest.raises(ValueError):
        await ports.evolutions.list_records("beta", limit=2, cursor=cursor)
    run_cursor = (await ports.runs.list_runs("alpha", purpose=None, limit=1, cursor=None))[1]
    assert run_cursor is not None
    with pytest.raises(ValueError):
        await ports.evolutions.list_records("alpha", limit=2, cursor=run_cursor)
    for invalid_limit in (0, -1, 101):
        with pytest.raises(ValueError):
            await ports.evolutions.list_records("alpha", limit=invalid_limit, cursor=None)
    await storage.close()


@pytest.mark.asyncio
async def test_reads_do_not_write_and_legacy_optional_fields_stay_unknown(tmp_path):
    storage, ports = await _storage(tmp_path)
    secret = "must-not-leak"
    await storage.register_model(
        ModelEndpoint.model_validate(
            {
                "ref": {"id": "fake", "version": "1"},
                "model_name": "fake-model",
                "base_url": "https://example.com/v1",
                "api_key": secret,
                "timeout_seconds": 1,
                "max_output_tokens": 10,
                "temperature": 0,
                "top_p": 1,
            }
        )
    )
    strategy = _strategy("legacy", 0)
    await ports.strategies.save(strategy)
    sealed, snapshot = _sealed_run(strategy, "legacy-run", RunPurpose.ONLINE, datetime.now(UTC))
    sealed_data = sealed.model_dump(mode="json")
    sealed_data.pop("output_ref")
    snapshot_data = snapshot.model_dump(mode="json")
    snapshot_data["run"].pop("output_ref")
    record = _record("legacy", "legacy-evolution")
    record_data = record.model_dump(mode="json")
    record_data.pop("termination_reason")
    with storage._connect().begin() as connection:
        connection.execute(
            runs.insert().values(
                run_id=sealed.run_id,
                strategy_id="legacy",
                version=0,
                scope=sealed.task_scope,
                purpose=sealed.purpose.value,
                sealed_at=sealed.sealed_at.isoformat(),
                snapshot=json.dumps(snapshot_data),
                sealed=json.dumps(sealed_data),
            )
        )
        connection.execute(
            evolutions.insert().values(
                evolution_id=record.evolution_id,
                strategy_id="legacy",
                data=json.dumps(record_data),
            )
        )

    def counts() -> dict[str, int]:
        with storage._connect().connect() as connection:
            return {
                table.name: connection.execute(select(func.count()).select_from(table)).scalar_one()
                for table in metadata.sorted_tables
            }

    before = counts()
    loaded_run = await ports.runs.get_sealed_run("legacy-run")
    loaded_snapshot = await ports.runs.read_snapshot("legacy-run")
    loaded_versions = await ports.strategies.list_versions("legacy")
    loaded_records, _ = await ports.evolutions.list_records("legacy", limit=10, cursor=None)
    after = counts()

    assert loaded_run.output_ref is None
    assert loaded_snapshot.run.output_ref is None
    assert loaded_records[0].termination_reason is None
    serialized = "".join(item.model_dump_json() for item in (*loaded_versions, loaded_run))
    assert secret not in serialized
    assert before == after
    await storage.close()
