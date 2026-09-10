"""N4 真实实验入口；先冻结配置，再在硬请求上限内执行。"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evoteam.composition import build_application
from evoteam.domain.agent import AgentConfig, AgentMessage, AgentResult
from evoteam.domain.common import AssetRef
from evoteam.domain.dataset import DatasetPartition
from evoteam.domain.run import RunStatus
from evoteam.evolution.datasets import ManifestDatasets
from evoteam.experiment_manifest import prepare_experiment
from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
from evoteam.runtime.protocol import AgentRuntime, RuntimeAgent, RuntimeContext
from evoteam.settings import Settings
from evoteam.storage.sqlite import SQLiteStorage


@dataclass
class RequestLimitedRuntime:
    delegate: AgentRuntime
    maximum_requests: int
    requests_used: int = 0

    async def create_agent(self, config: AgentConfig, *, run_id: str) -> RuntimeAgent:
        return await self.delegate.create_agent(config, run_id=run_id)

    async def invoke(
        self, agent: RuntimeAgent, message: AgentMessage, context: RuntimeContext
    ) -> AgentResult:
        if self.requests_used >= self.maximum_requests:
            raise RuntimeError("实验已达到预注册模型请求上限")
        self.requests_used += 1
        return await self.delegate.invoke(agent, message, context)

    async def close(self, agent: RuntimeAgent) -> None:
        await self.delegate.close(agent)


async def run_baseline(
    repository: Path, config_path: Path, output_dir: Path, settings: Settings
) -> dict[str, Any]:
    """执行一次不可续跑的固定 v0 History 基线，并返回脱敏报告。"""
    if output_dir.exists():
        raise ValueError("实验输出目录已存在；禁止覆盖或隐式续跑")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("phase") != "baseline" or config.get("approved_scope") != "fixed_v0_history_only":
        raise ValueError("当前入口只接受已批准的固定 v0 History 基线")
    if config.get("candidate_comparison_enabled") or config.get("final_test_enabled"):
        raise ValueError("基线批次不得运行候选比较或 Final Test")

    # 固定身份后，所有语义校验和执行终止均保存最终状态。
    prepared = prepare_experiment(repository, config_path, output_dir, settings)
    config = prepared.config
    strategy = prepared.strategy
    model = prepared.model
    database = output_dir / "evidence.db"
    storage = SQLiteStorage(f"sqlite:///{database}")
    runtime: RequestLimitedRuntime | None = None
    report = {
        **prepared.snapshot,
        "sampling": {"repeats": config["repeats"], "seed_applied": False},
        "request_limit": config["maximum_model_requests"],
        "requests_used": 0,
        "runs": [],
        "status": "running",
    }
    try:
        maximum_requests = int(config["maximum_model_requests"])
        dataset_ref = AssetRef.model_validate(config["dataset_ref"])
        datasets = ManifestDatasets(prepared.manifest)
        tasks = datasets.load(dataset_ref, partition=DatasetPartition.HISTORY)
        if len(tasks) != int(config["expected_task_count"]):
            raise ValueError("History 任务数量与预注册配置不一致")
        expected_requests = (
            len(tasks) * int(config["repeats"]) * int(config["expected_agent_calls_per_task"])
        )
        if expected_requests > maximum_requests:
            raise ValueError("预期调用数超过硬请求上限")
        runtime = RequestLimitedRuntime(
            OpenJiuwenRuntimeAdapter(models=(model,)), maximum_requests=maximum_requests
        )
        await storage.initialize()
        await storage.register_model(model)
        ports = await storage.open()
        await ports.strategies.save(strategy)
        app = build_application(runtime=runtime, storage=ports)
        for _repeat in range(int(config["repeats"])):
            for task in tasks:
                sealed = await app.tasks.execute(
                    task,
                    strategy_id=strategy.metadata.ref.strategy_id,
                    dataset_source=datasets.source_for(task, partition=DatasetPartition.HISTORY),
                )
                report["runs"].append(sealed.model_dump(mode="json"))
                if sealed.status == RunStatus.CANCELLED:
                    raise asyncio.CancelledError()
        report["status"] = "completed"
    except (asyncio.CancelledError, KeyboardInterrupt):
        report["status"] = "cancelled"
        raise
    except Exception:
        report["status"] = "failed"
        raise
    finally:
        report["requests_used"] = runtime.requests_used if runtime else 0
        with (output_dir / "baseline_report.json").open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        await storage.close()
    return report
