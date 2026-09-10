"""本地 API 的无外部请求契约测试。"""

from typing import Any

from fastapi.testclient import TestClient

from evoteam.api import create_app
from evoteam.settings import Settings


def test_api_health_does_not_require_a_model_connection():
    settings = Settings(
        **dict[str, Any](
            _env_file=None,
            model_id="deepseek-v4-flash",
            model_version="api-2026-09",
            model_name="deepseek-v4-flash",
        )
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model_id": "deepseek-v4-flash",
        "model_version": "api-2026-09",
        "model_name": "deepseek-v4-flash",
    }


def test_api_exposes_initialize_run_observe_and_evolve_contracts():
    schema = create_app(Settings(**dict[str, Any](_env_file=None))).openapi()
    assert {"/health", "/v1/initialize", "/v1/runs", "/v1/observe", "/v1/evolve"} <= set(
        schema["paths"]
    )


def test_unknown_strategy_returns_not_found(tmp_path):
    import asyncio
    import json
    from pathlib import Path

    from evoteam.storage.sqlite import SQLiteStorage

    database = tmp_path / "api.sqlite3"

    async def initialize():
        storage = SQLiteStorage(f"sqlite:///{database}")
        await storage.initialize()
        await storage.close()

    asyncio.run(initialize())
    settings = Settings(**dict[str, Any](_env_file=None, database_url=f"sqlite:///{database}"))
    policy = json.loads(
        (Path(__file__).parents[1] / "examples/monitor_policy.example.json").read_text()
    )
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/observe",
            json={"strategy_id": "missing", "task_scope": "project_planning", "policy": policy},
        )
    assert response.status_code == 404
