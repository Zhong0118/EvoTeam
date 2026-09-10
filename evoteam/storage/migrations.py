"""显式、可备份的 SQLite schema 升级；不读取或改写业务 JSON 证据。"""

import os
import sqlite3
import tempfile
from collections.abc import Sequence
from pathlib import Path

CURRENT_SCHEMA_VERSION = 3

_BASE_TABLES = frozenset(
    {"model_configs", "experiences", "monitor_states", "strategies", "runs", "events"}
)
_TEAM_TABLES = _BASE_TABLES | frozenset(
    {"strategy_counters", "evolutions", "attributions", "mutation_proposals", "validations"}
)
_CURRENT_TABLES = _TEAM_TABLES | frozenset({"evolution_claims"})
_LAYOUTS = {
    _BASE_TABLES: ("base-six-table", 1),
    _TEAM_TABLES: ("team-eleven-table", 2),
    _CURRENT_TABLES: ("current-twelve-table", CURRENT_SCHEMA_VERSION),
}

# (column name, SQLite declared type, NOT NULL, primary-key position)
_COLUMNS: dict[str, tuple[tuple[str, str, int, int], ...]] = {
    "model_configs": (
        ("model_id", "VARCHAR", 1, 1),
        ("version", "VARCHAR", 1, 2),
        ("data", "TEXT", 1, 0),
    ),
    "experiences": (
        ("record_id", "VARCHAR", 1, 1),
        ("kind", "VARCHAR", 1, 0),
        ("strategy_id", "VARCHAR", 1, 0),
        ("version", "INTEGER", 1, 0),
        ("scope", "VARCHAR", 1, 0),
        ("data", "TEXT", 1, 0),
    ),
    "monitor_states": (
        ("key", "VARCHAR", 1, 1),
        ("revision", "INTEGER", 1, 0),
        ("data", "TEXT", 1, 0),
    ),
    "strategies": (
        ("strategy_id", "VARCHAR", 1, 1),
        ("version", "INTEGER", 1, 2),
        ("serving_id", "VARCHAR", 0, 0),
        ("data", "TEXT", 1, 0),
    ),
    "strategy_counters": (
        ("strategy_id", "VARCHAR", 1, 1),
        ("last_version", "INTEGER", 1, 0),
    ),
    "evolutions": (
        ("evolution_id", "VARCHAR", 1, 1),
        ("strategy_id", "VARCHAR", 1, 0),
        ("data", "TEXT", 1, 0),
    ),
    "evolution_claims": (
        ("evolution_id", "VARCHAR", 1, 1),
        ("request_fingerprint", "VARCHAR", 1, 0),
        ("active_strategy_id", "VARCHAR", 0, 0),
    ),
    "attributions": (("report_id", "VARCHAR", 1, 1), ("data", "TEXT", 1, 0)),
    "mutation_proposals": (
        ("proposal_id", "VARCHAR", 1, 1),
        ("data", "TEXT", 1, 0),
    ),
    "validations": (("validation_id", "VARCHAR", 1, 1), ("data", "TEXT", 1, 0)),
    "runs": (
        ("run_id", "VARCHAR", 1, 1),
        ("strategy_id", "VARCHAR", 1, 0),
        ("version", "INTEGER", 1, 0),
        ("scope", "VARCHAR", 1, 0),
        ("purpose", "VARCHAR", 1, 0),
        ("sealed_at", "VARCHAR", 1, 0),
        ("snapshot", "TEXT", 1, 0),
        ("sealed", "TEXT", 1, 0),
    ),
    "events": (
        ("event_id", "VARCHAR", 1, 1),
        ("run_id", "VARCHAR", 1, 0),
        ("sequence", "INTEGER", 1, 0),
        ("data", "TEXT", 1, 0),
    ),
}

_CREATE_SQL = {
    "strategy_counters": """
        CREATE TABLE strategy_counters (
            strategy_id VARCHAR NOT NULL PRIMARY KEY,
            last_version INTEGER NOT NULL
        )
    """,
    "evolutions": """
        CREATE TABLE evolutions (
            evolution_id VARCHAR NOT NULL PRIMARY KEY,
            strategy_id VARCHAR NOT NULL,
            data TEXT NOT NULL
        )
    """,
    "evolution_claims": """
        CREATE TABLE evolution_claims (
            evolution_id VARCHAR NOT NULL PRIMARY KEY,
            request_fingerprint VARCHAR NOT NULL,
            active_strategy_id VARCHAR UNIQUE
        )
    """,
    "attributions": """
        CREATE TABLE attributions (
            report_id VARCHAR NOT NULL PRIMARY KEY,
            data TEXT NOT NULL
        )
    """,
    "mutation_proposals": """
        CREATE TABLE mutation_proposals (
            proposal_id VARCHAR NOT NULL PRIMARY KEY,
            data TEXT NOT NULL
        )
    """,
    "validations": """
        CREATE TABLE validations (
            validation_id VARCHAR NOT NULL PRIMARY KEY,
            data TEXT NOT NULL
        )
    """,
}


def _connect(database: Path, *, read_only: bool = False) -> sqlite3.Connection:
    mode = "ro" if read_only else "rw"
    return sqlite3.connect(f"{database.as_uri()}?mode={mode}", uri=True, isolation_level=None)


def _table_names(connection: sqlite3.Connection) -> frozenset[str]:
    return frozenset(
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    )


def _column_signature(
    connection: sqlite3.Connection, table: str
) -> tuple[tuple[str, str, int, int], ...]:
    # table 已先与内部白名单布局匹配，不接受外部标识符。
    return tuple(
        (row[1], row[2].upper(), row[3], row[5])
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    )


def _identify_layout(connection: sqlite3.Connection) -> str:
    tables = _table_names(connection)
    recognized = _LAYOUTS.get(tables)
    if recognized is None:
        raise ValueError("数据库表布局未知，拒绝自动迁移")
    layout, layout_version = recognized
    for table in tables:
        if _column_signature(connection, table) != _COLUMNS[table]:
            raise ValueError(f"数据库表 {table} 的列结构未知，拒绝自动迁移")
    user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if user_version not in {0, layout_version}:
        raise ValueError("Schema 版本与实际表布局不一致")
    return layout


def _backup_database(source: Path, destination: Path) -> None:
    source_connection = _connect(source, read_only=True)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        check = destination_connection.execute("PRAGMA quick_check").fetchone()
        if check is None or check[0] != "ok":
            raise OSError("SQLite 备份完整性检查失败")
    finally:
        destination_connection.close()
        source_connection.close()


def _create_tables(connection: sqlite3.Connection, names: Sequence[str]) -> None:
    for name in names:
        connection.execute(_CREATE_SQL[name])


def _apply_schema_upgrade(connection: sqlite3.Connection, layout: str) -> None:
    if layout == "base-six-table":
        _create_tables(
            connection,
            (
                "strategy_counters",
                "evolutions",
                "attributions",
                "mutation_proposals",
                "validations",
                "evolution_claims",
            ),
        )
        connection.execute(
            "INSERT INTO strategy_counters (strategy_id, last_version) "
            "SELECT strategy_id, MAX(version) FROM strategies GROUP BY strategy_id"
        )
    elif layout == "team-eleven-table":
        _create_tables(connection, ("evolution_claims",))
    elif layout != "current-twelve-table":
        raise ValueError("数据库布局未知，拒绝自动迁移")


def _preflight(database: Path, backup: Path) -> str:
    if not database.is_file():
        raise FileNotFoundError(database)
    if backup.exists() or backup.is_symlink():
        raise FileExistsError(backup)
    if not backup.parent.is_dir():
        raise FileNotFoundError(backup.parent)
    connection = _connect(database, read_only=True)
    try:
        return _identify_layout(connection)
    finally:
        connection.close()


def upgrade_database(database: Path, *, backup: Path) -> None:
    """备份并把已识别历史库升级到当前 schema；调用期间必须停止应用写入。"""
    database = Path(os.path.abspath(database))
    backup = Path(os.path.abspath(backup))
    expected_layout = _preflight(database, backup)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{backup.name}.", suffix=".tmp", dir=backup.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        _backup_database(database, temporary)
        os.replace(temporary, backup)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    connection = _connect(database)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        actual_layout = _identify_layout(connection)
        if actual_layout != expected_layout:
            raise ValueError("备份后数据库布局发生变化，拒绝继续迁移")
        _apply_schema_upgrade(connection, actual_layout)
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
        if _identify_layout(connection) != "current-twelve-table":
            raise ValueError("升级后的数据库布局校验失败")
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
