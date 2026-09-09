"""正式单机入口：显式登记初始策略，然后执行任务；不自动晋级或演进。"""

from pathlib import Path

from evoteam.composition import build_application
from evoteam.domain.evolution import MonitorResult
from evoteam.domain.run import RunPurpose, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.orchestration.orchestrator import validate_v0
from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
from evoteam.settings import Settings
from evoteam.storage.sqlite import SQLiteStorage


async def initialize_database(database: Path, strategy: Strategy, settings: Settings) -> None:
    model = settings.runtime_model()
    validate_v0(strategy, RunPurpose.ONLINE)
    if strategy.metadata.status != StrategyStatus.CURRENT or strategy.metadata.parent is not None:
        raise ValueError("初始化只接受无父版本的 CURRENT 基线；不能代替晋级")
    if any(agent.model_ref != model.ref for agent in strategy.definition.agents):
        raise ValueError("策略模型引用与环境登记不一致")
    database = database.resolve()
    with database.open("xb"):
        pass
    storage = SQLiteStorage(f"sqlite:///{database}")
    try:
        await storage.initialize()
        await storage.register_model(model)
        ports = await storage.open()
        await ports.strategies.save(strategy)
    finally:
        await storage.close()


async def run_task(
    database: Path, task: Task, *, strategy_id: str, settings: Settings
) -> SealedRun:
    if not database.is_file():
        raise ValueError("数据库不存在，请先 init")
    model = settings.runtime_model()
    storage = SQLiteStorage(f"sqlite:///{database.resolve()}")
    try:
        ports = await storage.open()
        await storage.require_model(model)
        app = build_application(runtime=OpenJiuwenRuntimeAdapter(models=(model,)), storage=ports)
        return await app.tasks.execute(task, strategy_id=strategy_id)
    finally:
        await storage.close()


async def observe_history(
    database: Path, *, strategy_id: str, task_scope: str, policy: EvolutionPolicy
) -> MonitorResult:
    """显式观察既有历史，不连接模型、不生成 Candidate。"""
    if not database.is_file():
        raise ValueError("数据库不存在")
    storage = SQLiteStorage(f"sqlite:///{database.resolve()}")
    try:
        ports = await storage.open()
        app = build_application(runtime=OpenJiuwenRuntimeAdapter(), storage=ports)
        observation = await app.evolution.inspect(
            strategy_id=strategy_id, task_scope=task_scope, policy=policy
        )
        return observation.result
    finally:
        await storage.close()
