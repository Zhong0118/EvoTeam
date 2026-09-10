"""本地 FastAPI 入口。

使用服务端配置的模型和 SQLite，不接收任意文件路径。
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from evoteam.domain.evolution import EvolutionRecord, MonitorResult, ValidationPlan
from evoteam.domain.run import SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task
from evoteam.entrypoints import evolve_history, initialize_database, observe_history, run_task
from evoteam.evolution.gate import GatePolicy
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.settings import Settings


class InitializeRequest(BaseModel):
    strategy: Strategy


class RunRequest(BaseModel):
    task: Task
    strategy_id: Annotated[str, Field(min_length=1, max_length=128)]


class ObserveRequest(BaseModel):
    strategy_id: Annotated[str, Field(min_length=1, max_length=128)]
    task_scope: Annotated[str, Field(min_length=1, max_length=128)]
    policy: EvolutionPolicy


class EvolveRequest(ObserveRequest):
    validation_plan: ValidationPlan
    gate_policy: GatePolicy


def _database_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("本地 API 当前只支持 sqlite:/// 文件数据库")
    value = database_url[len(prefix) :]
    if not value or value == ":memory:":
        raise ValueError("本地 API 需要持久化 SQLite 文件")
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def _safe_bad_request(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error": type(exc).__name__, "message": "请求或服务端配置不合法"},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """由 uvicorn --factory 调用；导入模块不会连接模型或数据库。"""
    configured = settings or Settings()
    app = FastAPI(title="EvoTeam API", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "model_id": configured.model_id,
            "model_version": configured.model_version,
            "model_name": configured.model_name,
        }

    @app.post("/v1/initialize", status_code=201)
    async def initialize(request: InitializeRequest) -> dict[str, bool]:
        try:
            await initialize_database(
                _database_path(configured.database_url), request.strategy, configured
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="策略或版本化资源不存在") from exc
        except (OSError, ValueError) as exc:
            raise _safe_bad_request(exc) from exc
        return {"initialized": True}

    @app.post("/v1/runs", response_model=SealedRun)
    async def run(request: RunRequest) -> SealedRun:
        try:
            return await run_task(
                _database_path(configured.database_url),
                request.task,
                strategy_id=request.strategy_id,
                settings=configured,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="策略或版本化资源不存在") from exc
        except (OSError, ValueError) as exc:
            raise _safe_bad_request(exc) from exc

    @app.post("/v1/observe", response_model=MonitorResult)
    async def observe(request: ObserveRequest) -> MonitorResult:
        try:
            return await observe_history(
                _database_path(configured.database_url),
                strategy_id=request.strategy_id,
                task_scope=request.task_scope,
                policy=request.policy,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="策略或版本化资源不存在") from exc
        except (OSError, ValueError) as exc:
            raise _safe_bad_request(exc) from exc

    @app.post("/v1/evolve", response_model=EvolutionRecord | None)
    async def evolve(request: EvolveRequest) -> EvolutionRecord | None:
        try:
            return await evolve_history(
                _database_path(configured.database_url),
                strategy_id=request.strategy_id,
                task_scope=request.task_scope,
                policy=request.policy,
                validation_plan=request.validation_plan,
                gate_policy=request.gate_policy,
                settings=configured,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="策略或版本化资源不存在") from exc
        except (OSError, ValueError) as exc:
            raise _safe_bad_request(exc) from exc

    return app
