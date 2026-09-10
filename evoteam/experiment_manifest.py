"""不可覆盖的实验前置身份快照；所有内容在首次 Runtime 调用前读取。"""

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evoteam.capabilities.prompts import load_prompt
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.dataset import DatasetManifest
from evoteam.domain.strategy import Strategy
from evoteam.runtime.models import ModelEndpoint
from evoteam.settings import Settings


@dataclass(frozen=True)
class PreparedExperiment:
    config: dict[str, Any]
    manifest: DatasetManifest
    strategy: Strategy
    model: ModelEndpoint
    snapshot: dict[str, Any]


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()


def prepare_experiment(
    repository: Path, config_path: Path, output_dir: Path, settings: Settings
) -> PreparedExperiment:
    """验证实际身份并独占创建输出目录；不连接模型，不保存凭据。"""
    if output_dir.exists():
        raise ValueError("实验输出目录已存在；禁止覆盖或隐式续跑")
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    evaluator = AssetRef(id="project-planning-rules", version="1")
    if AssetRef.model_validate(config["evaluator_ref"]) != evaluator:
        raise ValueError("预注册评价器与实际评价器不一致")
    manifest_bytes = (repository / "examples/datasets/project_planning_manifest.json").read_bytes()
    strategy_bytes = (repository / config["strategy_file"]).read_bytes()
    manifest = DatasetManifest.model_validate_json(manifest_bytes)
    strategy = Strategy.model_validate_json(strategy_bytes)
    if manifest.ref != AssetRef.model_validate(config["manifest_ref"]):
        raise ValueError("实验配置与数据清单版本不一致")
    if strategy.metadata.ref != StrategyRef.model_validate(config["strategy_ref"]):
        raise ValueError("实验配置与 Strategy 引用不一致")
    model = settings.runtime_model()
    if any(agent.model_ref != model.ref for agent in strategy.definition.agents):
        raise ValueError("Strategy 模型引用与环境登记不一致")
    model_metadata = model.model_dump(mode="json", exclude={"base_url"})
    if "expected_model" in config and config["expected_model"] != model_metadata:
        raise ValueError("实际模型参数与预注册模型配置不一致")
    commit = _git(repository, "rev-parse", "HEAD")
    dirty = bool(_git(repository, "status", "--porcelain", "--untracked-files=no"))
    if dirty:
        raise ValueError("实验代码存在未提交的已跟踪修改；请先固定代码提交")
    prompt_refs = [agent.prompt_ref for agent in strategy.definition.agents]
    prompt_refs.extend(
        AssetRef.model_validate(ref) for ref in config.get("additional_prompt_refs", [])
    )
    sources = []
    for ref in dict.fromkeys(prompt_refs):
        content = load_prompt(ref)
        sources.append(
            {
                "ref": ref.model_dump(mode="json"),
                "content": content,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )
    snapshot = {
        "experiment_id": config["experiment_id"],
        "code_commit": commit,
        "code_dirty": dirty,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "strategy_sha256": hashlib.sha256(strategy_bytes).hexdigest(),
        "config": config,
        "manifest": json.loads(manifest_bytes),
        "strategy": json.loads(strategy_bytes),
        "model": model_metadata,
        "evaluator_ref": evaluator.model_dump(mode="json"),
        "prompt_refs": [ref.model_dump(mode="json") for ref in prompt_refs],
        "prompt_sources": sources,
        "budget": strategy.definition.orchestration.budget.model_dump(mode="json"),
    }
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise ValueError("实验输出目录已存在；禁止覆盖或隐式续跑") from None
    with (output_dir / "preflight.json").open("x", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
    return PreparedExperiment(config, manifest, strategy, model, snapshot)
