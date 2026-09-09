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
