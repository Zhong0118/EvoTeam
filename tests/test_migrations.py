"""N1 explicit SQLite migration tests using the repository's historical layouts."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select

from evoteam.bootstrap import build_v0_strategy
from evoteam.cli import main
from evoteam.domain.common import AssetRef
from evoteam.domain.evaluation import EvaluationResult, RunMetrics
from evoteam.domain.events import EventType, TraceEvent
from evoteam.domain.run import RunPurpose, RunResult, RunSnapshot, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task, TaskType
from evoteam.storage.migrations import CURRENT_SCHEMA_VERSION, upgrade_database
from evoteam.storage.sqlite import (
    SQLiteStorage,
    attributions,
    events,
    evolution_claims,
    evolutions,
    experiences,
    metadata,
    model_configs,
    monitor_states,
    mutation_proposals,
    runs,
    strategies,
    strategy_counters,
    validations,
)

BASE_TABLES = (
    model_configs,
    experiences,
    monitor_states,
    strategies,
    runs,
    events,
)
TEAM_TABLES = BASE_TABLES + (
    strategy_counters,
    evolutions,
    attributions,
    mutation_proposals,
    validations,
)
CURRENT_TABLES = TEAM_TABLES + (evolution_claims,)


def _strategy() -> Strategy:
    value = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).model_dump()
    value["metadata"]["status"] = StrategyStatus.CURRENT
    return Strategy.model_validate(value)


def _evidence() -> tuple[Strategy, TraceEvent, SealedRun, RunSnapshot]:
    strategy = _strategy()
    task = Task(
        task_id="migration-task",
        task_type=TaskType.PROJECT_PLANNING,
        instruction="preserve exactly",
        input_schema=AssetRef(id="planning-task", version="1"),
        inputs={"fixed": True},
    )
    result = RunResult(
        run_id="migration-run",
        task_id=task.task_id,
        strategy=strategy.metadata.ref,
        purpose=RunPurpose.ONLINE,
        status=RunStatus.COMPLETED,
        trace_refs=("migration-event",),
        output_ref="artifact:fixed",
    )
    event = TraceEvent(
        event_id="migration-event",
        event_type=EventType.TASK_CREATED,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        sequence=0,
        run_id=result.run_id,
        task_id=task.task_id,
        strategy=strategy.metadata.ref,
        payload={"fixed": True},
    )
    sealed = SealedRun(
        run_id=result.run_id,
        task_id=task.task_id,
        task_scope=task.task_type.value,
        strategy=strategy.metadata.ref,
        purpose=result.purpose,
        status=result.status,
        sealed_at=datetime(2026, 1, 2, tzinfo=UTC),
        snapshot_ref="sqlite:run:migration-run",
        trace_refs=(event.event_id,),
        evaluation=EvaluationResult(
            run_id=result.run_id,
            evaluator_ref=AssetRef(id="rules", version="1"),
            metrics=RunMetrics(success=True, tokens=7),
        ),
        output_ref=result.output_ref,
    )
    return strategy, event, sealed, RunSnapshot(task=task, strategy=strategy, run=result)


def _create_historical_database(database: Path, tables) -> tuple[SealedRun, RunSnapshot]:
    engine = create_engine(f"sqlite:///{database}")
    for table in tables:
        table.create(engine)
    strategy, event, sealed, snapshot = _evidence()
    with engine.begin() as connection:
        connection.execute(
            strategies.insert().values(
                strategy_id=strategy.metadata.ref.strategy_id,
                version=strategy.metadata.ref.version,
                serving_id=strategy.metadata.ref.strategy_id,
                data=strategy.model_dump_json(),
            )
        )
        connection.execute(
            events.insert().values(
                event_id=event.event_id,
                run_id=event.run_id,
                sequence=event.sequence,
                data=event.model_dump_json(),
            )
        )
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
        if strategy_counters in tables:
            connection.execute(
                strategy_counters.insert().values(
                    strategy_id=strategy.metadata.ref.strategy_id,
                    last_version=strategy.metadata.ref.version,
                )
            )
        if evolution_claims in tables:
            connection.execute(
                evolution_claims.insert().values(
                    evolution_id="active-evolution",
                    request_fingerprint="fixed-fingerprint",
                    active_strategy_id=strategy.metadata.ref.strategy_id,
                )
            )
    engine.dispose()
    return sealed, snapshot


def _raw_evidence(database: Path) -> dict[str, tuple]:
    engine = create_engine(f"sqlite:///{database}")
    with engine.connect() as connection:
        result = {
            "strategies": tuple(connection.execute(select(strategies)).mappings()),
            "events": tuple(connection.execute(select(events)).mappings()),
            "runs": tuple(connection.execute(select(runs)).mappings()),
        }
    engine.dispose()
    return result


def _table_names(database: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{database}")
    names = set(inspect(engine).get_table_names())
    engine.dispose()
    return names


def _schema_version(database: Path) -> int:
    engine = create_engine(f"sqlite:///{database}")
    with engine.connect() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
    engine.dispose()
    return version


@pytest.mark.asyncio
@pytest.mark.parametrize("historical_tables", [BASE_TABLES, TEAM_TABLES, CURRENT_TABLES])
async def test_upgrade_preserves_evidence_and_opens_current_storage(tmp_path, historical_tables):
    database = tmp_path / "history.db"
    backup = tmp_path / "history.backup.db"
    sealed, snapshot = _create_historical_database(database, historical_tables)
    original = _raw_evidence(database)

    upgrade_database(database, backup=backup)

    assert backup.exists()
    assert _raw_evidence(backup) == original
    assert _raw_evidence(database) == original
    assert _table_names(database) == set(metadata.tables)
    assert _schema_version(database) == CURRENT_SCHEMA_VERSION
    storage = SQLiteStorage(f"sqlite:///{database}")
    ports = await storage.open()
    assert await ports.runs.get_sealed_run(sealed.run_id) == sealed
    assert await ports.runs.read_snapshot(sealed.run_id) == snapshot
    if historical_tables == BASE_TABLES:
        assert (await ports.strategies.allocate_version("project-planning")).version == 1
    if historical_tables == CURRENT_TABLES:
        with storage._connect().connect() as connection:
            claim = connection.execute(select(evolution_claims)).mappings().one()
        assert dict(claim) == {
            "evolution_id": "active-evolution",
            "request_fingerprint": "fixed-fingerprint",
            "active_strategy_id": "project-planning",
        }
    await storage.close()


def test_second_upgrade_does_not_change_evidence(tmp_path):
    database = tmp_path / "history.db"
    _create_historical_database(database, BASE_TABLES)
    upgrade_database(database, backup=tmp_path / "before-first.db")
    after_first = _raw_evidence(database)

    upgrade_database(database, backup=tmp_path / "before-second.db")

    assert _raw_evidence(database) == after_first
    assert _schema_version(database) == CURRENT_SCHEMA_VERSION


@pytest.mark.asyncio
async def test_initialize_and_open_cannot_bypass_explicit_migration(tmp_path):
    database = tmp_path / "history.db"
    _create_historical_database(database, BASE_TABLES)
    storage = SQLiteStorage(f"sqlite:///{database}")

    with pytest.raises(ValueError, match="migrate"):
        await storage.initialize()
    with pytest.raises(ValueError):
        await storage.open()

    assert _table_names(database) == {table.name for table in BASE_TABLES}
    assert _schema_version(database) == 0
    await storage.close()


@pytest.mark.parametrize(
    "case", ["missing_database", "existing_backup", "unknown_columns", "unknown_table"]
)
def test_preflight_failures_do_not_modify_database_or_create_backup(tmp_path, case):
    database = tmp_path / "history.db"
    backup = tmp_path / "backup.db"
    if case != "missing_database":
        _create_historical_database(database, BASE_TABLES)
    if case == "existing_backup":
        backup.write_text("do not overwrite")
    if case == "unknown_columns":
        engine = create_engine(f"sqlite:///{database}")
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE runs ADD COLUMN invented TEXT")
        engine.dispose()
    if case == "unknown_table":
        engine = create_engine(f"sqlite:///{database}")
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE invented (value TEXT)")
        engine.dispose()
    tables_before = _table_names(database) if database.exists() else set()

    with pytest.raises((FileExistsError, FileNotFoundError, ValueError)):
        upgrade_database(database, backup=backup)

    if case != "existing_backup":
        assert not backup.exists()
    if database.exists():
        assert _table_names(database) == tables_before
        assert _schema_version(database) == 0


def test_backup_failure_does_not_start_migration(tmp_path, monkeypatch):
    from evoteam.storage import migrations

    database = tmp_path / "history.db"
    backup = tmp_path / "backup.db"
    _create_historical_database(database, BASE_TABLES)
    original_tables = _table_names(database)

    def fail_backup(source, destination):
        raise OSError("injected backup failure")

    monkeypatch.setattr(migrations, "_backup_database", fail_backup)
    with pytest.raises(OSError, match="injected"):
        upgrade_database(database, backup=backup)

    assert _table_names(database) == original_tables
    assert _schema_version(database) == 0
    assert not backup.exists()


def test_migration_failure_rolls_back_all_schema_changes(tmp_path, monkeypatch):
    from evoteam.storage import migrations

    database = tmp_path / "history.db"
    backup = tmp_path / "backup.db"
    _create_historical_database(database, BASE_TABLES)
    original_tables = _table_names(database)

    def fail_after_one_table(connection, layout):
        connection.execute("CREATE TABLE should_rollback (id INTEGER PRIMARY KEY)")
        raise RuntimeError("injected migration failure")

    monkeypatch.setattr(migrations, "_apply_schema_upgrade", fail_after_one_table)
    with pytest.raises(RuntimeError, match="injected"):
        upgrade_database(database, backup=backup)

    assert backup.exists()
    assert _table_names(database) == original_tables
    assert _schema_version(database) == 0


def test_cli_migrate_requires_explicit_paths_and_reports_success(tmp_path, capsys):
    database = tmp_path / "history.db"
    backup = tmp_path / "backup.db"
    _create_historical_database(database, TEAM_TABLES)

    assert main(["migrate", "--database", str(database), "--backup", str(backup)]) == 0

    assert capsys.readouterr().out.strip() == '{"migrated": true, "schema_version": 3}'
    assert backup.exists()
    assert _schema_version(database) == CURRENT_SCHEMA_VERSION


@pytest.mark.parametrize("suffix", ["#1.db", "?1.db"])
def test_migration_targets_literal_filename_and_preserves_neighbor(tmp_path, suffix):
    import sqlite3

    neighbor = tmp_path / "history"
    target = tmp_path / f"history{suffix}"
    backup = tmp_path / "backup.db"
    _create_historical_database(neighbor, BASE_TABLES)
    # SQLAlchemy also parses ?; use sqlite backup to create the literal filename.
    with sqlite3.connect(neighbor) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    upgrade_database(target, backup=backup)
    with sqlite3.connect(target) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
    with sqlite3.connect(neighbor) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
