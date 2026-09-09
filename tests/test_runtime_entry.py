"""正式入口连接真实 SDK 和 SQLite；模型端使用本地 HTTP 协议服务。"""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from test_openjiuwen import completion_server

from evoteam.bootstrap import build_v0_strategy
from evoteam.domain.common import AssetRef
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task
from evoteam.settings import Settings

EXAMPLE = Path(__file__).parents[1] / "examples" / "project_planning"


def test_runtime_settings_require_explicit_values_without_printing_credentials(monkeypatch):
    import os

    for key in os.environ:
        if key.startswith("EVOTEAM_"):
            monkeypatch.delenv(key)
    with pytest.raises(ValueError, match="配置"):
        Settings(**dict[str, Any](_env_file=None)).runtime_model()


@pytest.mark.asyncio
async def test_live_entry_runs_three_real_sdk_calls_and_rejects_model_rebinding(tmp_path):
    from evoteam.entrypoints import initialize_database, run_task
    from evoteam.storage.sqlite import SQLiteStorage

    responses = [
        {"summary": "按依赖执行", "constraint_refs": []},
        json.loads((EXAMPLE / "plan.json").read_text()),
        {"passed": True, "issues": []},
    ]
    with completion_server(content=lambda index: json.dumps(responses[(index - 1) % 3])) as (
        url,
        calls,
    ):
        settings = Settings(
            **dict[str, Any](_env_file=None),
            model_id="fixture",
            model_version="1",
            model_name="fixture-model",
            model_base_url=url,
            model_api_key=SecretStr("test-only"),
            model_timeout_seconds=5,
            model_max_output_tokens=100,
            model_temperature=0,
            model_top_p=1,
        )
        data = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).model_dump()
        data["metadata"]["status"] = "current"
        data["definition"]["orchestration"]["budget"] = {
            "max_tokens": 1000,
            "max_tool_calls": 0,
            "timeout_seconds": 30,
        }
        for config in data["definition"]["agents"]:
            config["runtime_config"]["timeout_seconds"] = 10
        strategy = Strategy.model_validate(data)
        path = tmp_path / "live.db"
        await initialize_database(path, strategy, settings)
        result = await run_task(
            path,
            Task.model_validate_json((EXAMPLE / "task.json").read_text()),
            strategy_id="project-planning",
            settings=settings,
        )
        assert result.evaluation.metrics.success is True
        assert result.evaluation.metrics.tokens == 60
        assert result.evaluation.metrics.latency_seconds is not None
        assert len(calls) == 3
        storage = SQLiteStorage(f"sqlite:///{path}")
        ports = await storage.open()
        snapshot = await ports.runs.read_snapshot(result.run_id)
        assert len(snapshot.run.results) == 3
        await storage.close()
        # 真实SDK执行失败产物两次，再通过应用入口观察；不调用演进 Manager。
        from test_application import policy

        from evoteam.entrypoints import observe_history

        responses[1]["schedule"] = []
        for _ in range(2):
            failed = await run_task(
                path,
                Task.model_validate_json((EXAMPLE / "task.json").read_text()),
                strategy_id="project-planning",
                settings=settings,
            )
            assert failed.evaluation.metrics.success is False
        observed = await observe_history(
            path, strategy_id="project-planning", task_scope="project_planning", policy=policy()
        )
        assert observed.trigger is not None
        assert (
            await observe_history(
                path, strategy_id="project-planning", task_scope="project_planning", policy=policy()
            )
            == observed
        )
        # 同一 ref 改模型名不能悄悄改变已登记策略的行为。
        settings.model_name = "different-model"
        with pytest.raises(ValueError, match="模型"):
            await run_task(
                path,
                Task.model_validate_json((EXAMPLE / "task.json").read_text()),
                strategy_id="project-planning",
                settings=settings,
            )
        assert len(calls) == 9


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_real_sdk_timeout_and_external_cancel_are_archived(tmp_path, cancel):
    import asyncio

    from evoteam.entrypoints import initialize_database, run_task
    from evoteam.storage.sqlite import SQLiteStorage

    with completion_server(delay=0.6) as (url, requests):
        settings = Settings(
            **dict[str, Any](_env_file=None),
            model_id="fixture",
            model_version="1",
            model_name="fixture-model",
            model_base_url=url,
            model_api_key=SecretStr("test-only"),
            model_timeout_seconds=0.3,
            model_max_output_tokens=100,
            model_temperature=0,
            model_top_p=1,
        )
        data = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).model_dump()
        data["metadata"]["status"] = "current"
        data["definition"]["orchestration"]["budget"] = {
            "max_tokens": 1000,
            "max_tool_calls": 0,
            "timeout_seconds": 30,
        }
        for config in data["definition"]["agents"]:
            config["runtime_config"]["timeout_seconds"] = 2
        database = tmp_path / "timeout.db"
        await initialize_database(database, Strategy.model_validate(data), settings)
        worker = asyncio.create_task(
            run_task(
                database,
                Task.model_validate_json((EXAMPLE / "task.json").read_text()),
                strategy_id="project-planning",
                settings=settings,
            )
        )
        if cancel:
            async with asyncio.timeout(5):
                while not requests:
                    await asyncio.sleep(0.01)
            worker.cancel()
        result = await worker
        assert result.status.value == ("cancelled" if cancel else "timed_out")
        assert result.evaluation.metrics.success is False
        assert len(requests) == 1
        storage = SQLiteStorage(f"sqlite:///{database}")
        ports = await storage.open()
        assert (await ports.runs.events_for_run(result.run_id))[-1].event_type.value == "run_sealed"
        assert (await ports.runs.read_snapshot(result.run_id)).run.results == []
        await storage.close()


def test_real_cli_stdout_is_json_even_when_sdk_logs(tmp_path):
    import os
    import subprocess
    import sys

    from test_online import configured_strategy

    responses = [
        {"summary": "按依赖执行", "constraint_refs": []},
        json.loads((EXAMPLE / "plan.json").read_text()),
        {"passed": True, "issues": []},
    ]
    with completion_server(content=lambda index: json.dumps(responses[index - 1])) as (url, _):
        data = configured_strategy().model_dump()
        data["definition"]["orchestration"]["budget"]["timeout_seconds"] = 60
        for config in data["definition"]["agents"]:
            config["model_ref"] = {"id": "fixture", "version": "1"}
            config["runtime_config"]["timeout_seconds"] = 20
        strategy = tmp_path / "strategy.json"
        strategy.write_text(json.dumps(data))
        database = tmp_path / "cli.db"
        env = dict(
            os.environ,
            EVOTEAM_MODEL_ID="fixture",
            EVOTEAM_MODEL_VERSION="1",
            EVOTEAM_MODEL_NAME="fixture-model",
            EVOTEAM_MODEL_BASE_URL=url,
            EVOTEAM_MODEL_API_KEY="test-only",
            EVOTEAM_MODEL_TIMEOUT_SECONDS="10",
            EVOTEAM_MODEL_MAX_OUTPUT_TOKENS="100",
            EVOTEAM_MODEL_TEMPERATURE="0",
            EVOTEAM_MODEL_TOP_P="1",
        )
        base = [sys.executable, "-m", "evoteam"]
        init = subprocess.run(
            [*base, "init", "--database", str(database), "--strategy", str(strategy)],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert init.returncode == 0, init.stderr
        run = subprocess.run(
            [
                *base,
                "run",
                "--database",
                str(database),
                "--strategy-id",
                "project-planning",
                "--task",
                str(EXAMPLE / "task.json"),
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout)["status"] == "completed"
