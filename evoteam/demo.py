"""最小可运行演示：手写模型产物 + 真实调度/检查/SQLite，仅使用全新数据库。"""

import json
from pathlib import Path

from evoteam.bootstrap import build_v0_strategy
from evoteam.composition import build_application
from evoteam.domain.common import AssetRef
from evoteam.domain.planning import ANALYSIS_SCHEMA, PLAN_SCHEMA, REVIEW_SCHEMA
from evoteam.domain.role import RoleType
from evoteam.domain.run import SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task
from evoteam.runtime.fake import FakeRuntime, ScriptedOutput
from evoteam.storage.sqlite import SQLiteStorage


async def run_demo(database: Path) -> SealedRun:
    # 独占创建，拒绝重用真实历史库，避免演示污染后续 Monitor 证据。
    database = database.resolve()
    with database.open("xb"):
        pass
    example = Path(__file__).resolve().parents[1] / "examples" / "project_planning"
    task = Task.model_validate_json((example / "task.json").read_text())
    runtime = FakeRuntime(
        {
            RoleType.PLANNER: ScriptedOutput(
                ANALYSIS_SCHEMA,
                {"summary": "先设计再实现", "constraint_refs": ["deadline_hour", "budget_minor"]},
            ),
            RoleType.EXECUTOR: ScriptedOutput(
                PLAN_SCHEMA, json.loads((example / "plan.json").read_text())
            ),
            RoleType.CRITIC: ScriptedOutput(REVIEW_SCHEMA, {"passed": True, "issues": []}),
        }
    )
    data = build_v0_strategy(model_ref=AssetRef(id="fake", version="1")).model_dump()
    # 仅初始化独立演示库的服务版本；不是 Gate 晋级或实验校准结果。
    data["metadata"]["status"] = "current"
    data["metadata"]["ref"]["strategy_id"] = "demo-project-planning"
    data["definition"]["orchestration"]["budget"] = {
        "max_tokens": 100,
        "max_tool_calls": 0,
        "timeout_seconds": 10,
    }
    for config in data["definition"]["agents"]:
        config["runtime_config"]["timeout_seconds"] = 2
    strategy = Strategy.model_validate(data)
    storage = SQLiteStorage(f"sqlite:///{database}")
    try:
        await storage.initialize()
        ports = await storage.open()
        await ports.strategies.save(strategy)
        app = build_application(runtime=runtime, storage=ports)
        return await app.tasks.execute(task, strategy_id="demo-project-planning")
    finally:
        await storage.close()
