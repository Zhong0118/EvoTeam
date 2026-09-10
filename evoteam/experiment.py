"""N4 真实实验入口；先冻结配置，再在硬请求上限内执行。"""

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evoteam.composition import build_application
from evoteam.domain.agent import AgentConfig, AgentMessage, AgentResult
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.dataset import DatasetManifest, DatasetPartition
from evoteam.domain.strategy import Strategy
from evoteam.evolution.datasets import ManifestDatasets
from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
from evoteam.runtime.protocol import RuntimeAgent, RuntimeContext
from evoteam.settings import Settings
from evoteam.storage.sqlite import SQLiteStorage


@dataclass
class RequestLimitedRuntime:
    delegate: OpenJiuwenRuntimeAdapter
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(repository: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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

    manifest_path = repository / "examples/datasets/project_planning_manifest.json"
    strategy_path = repository / str(config["strategy_file"])
    manifest = DatasetManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    manifest_ref = AssetRef.model_validate(config["manifest_ref"])
    if manifest.ref != manifest_ref:
        raise ValueError("实验配置与数据清单版本不一致")
    dataset_ref = AssetRef.model_validate(config["dataset_ref"])
    tasks = ManifestDatasets(manifest).load(dataset_ref, partition=DatasetPartition.HISTORY)
    strategy = Strategy.model_validate_json(strategy_path.read_text(encoding="utf-8"))
    if strategy.metadata.ref != StrategyRef.model_validate(config["strategy_ref"]):
        raise ValueError("实验配置与 v0 Strategy 引用不一致")
    if len(tasks) != int(config["expected_task_count"]):
        raise ValueError("History 任务数量与预注册配置不一致")
    expected_requests = (
        len(tasks) * int(config["repeats"]) * int(config["expected_agent_calls_per_task"])
    )
    maximum_requests = int(config["maximum_model_requests"])
    if expected_requests > maximum_requests:
        raise ValueError("预期调用数超过硬请求上限")

    model = settings.runtime_model()
    if any(agent.model_ref != model.ref for agent in strategy.definition.agents):
        raise ValueError("Strategy 模型引用与环境登记不一致")

    output_dir.mkdir(parents=True)
    database = output_dir / "evidence.db"
    storage = SQLiteStorage(f"sqlite:///{database}")
    runtime = RequestLimitedRuntime(
        OpenJiuwenRuntimeAdapter(models=(model,)), maximum_requests=maximum_requests
    )
    sealed = []
    try:
        await storage.initialize()
        await storage.register_model(model)
        ports = await storage.open()
        await ports.strategies.save(strategy)
        app = build_application(runtime=runtime, storage=ports)
        for _repeat in range(int(config["repeats"])):
            for task in tasks:
                sealed.append(
                    await app.tasks.execute(task, strategy_id=strategy.metadata.ref.strategy_id)
                )
    finally:
        await storage.close()

    report = {
        "experiment_id": config["experiment_id"],
        "code_commit": _git_commit(repository),
        "config_sha256": _sha256(config_path),
        "manifest_sha256": _sha256(manifest_path),
        "strategy_sha256": _sha256(strategy_path),
        "model": {
            "ref": model.ref.model_dump(mode="json"),
            "model_name": model.model_name,
            "temperature": model.temperature,
            "top_p": model.top_p,
            "max_output_tokens": model.max_output_tokens,
            "timeout_seconds": model.timeout_seconds,
        },
        "prompt_refs": [
            agent.prompt_ref.model_dump(mode="json") for agent in strategy.definition.agents
        ],
        "budget": strategy.definition.orchestration.budget.model_dump(mode="json"),
        "evaluator_ref": config["evaluator_ref"],
        "sampling": {"repeats": config["repeats"], "seed_applied": False},
        "request_limit": maximum_requests,
        "requests_used": runtime.requests_used,
        "runs": [item.model_dump(mode="json") for item in sealed],
    }
    (output_dir / "baseline_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
