"""显式 opt-in 的真实模型冒烟；默认不产生外部请求或费用。"""

import os
from pathlib import Path

import pytest

from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task
from evoteam.entrypoints import initialize_database, run_task
from evoteam.settings import Settings


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("EVOTEAM_RUN_LIVE_TEST") != "1", reason="需要显式启用真实模型冒烟与有效 .env"
)
async def test_configured_live_provider_completes_project_planning(tmp_path):
    root = Path(__file__).parents[1]
    # 策略参数必须由用户先检查/配置，模型身份与 .env 登记保持一致。
    strategy = Strategy.model_validate_json(
        (root / "examples/project_planning/strategy.json").read_text()
    )
    task = Task.model_validate_json((root / "examples/project_planning/task.json").read_text())
    settings = Settings()
    database = tmp_path / "live-smoke.db"
    await initialize_database(database, strategy, settings)
    result = await run_task(
        database, task, strategy_id=strategy.metadata.ref.strategy_id, settings=settings
    )
    assert result.status.value == "completed", result.status
    assert result.evaluation.metrics.success is True, result.evaluation.issues
