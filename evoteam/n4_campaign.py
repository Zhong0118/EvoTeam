"""一次性预注册研究对照；不伪造 Monitor Trigger，不修改线上服务指针。"""

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from evoteam.composition import StoreEventSink
from evoteam.domain.common import AssetRef
from evoteam.domain.dataset import DatasetPartition
from evoteam.domain.evolution import MutationProposal, MutationType, ValidationPlan
from evoteam.domain.run import RunPurpose, RunStatus, SealedRun
from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.datasets import ManifestDatasets
from evoteam.evolution.gate import GatePolicy, ValidationGate
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import Validator
from evoteam.experiment import RequestLimitedRuntime
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.monitoring.strategy_monitor import StrategyMonitor
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.runtime.protocol import AgentRuntime
from evoteam.storage.sqlite import SQLiteStorage


def campaign_request_bound(config: dict[str, Any], datasets: ManifestDatasets) -> int:
    """固定三角色 v0、两种单因素候选、零 Retry 的最坏调用数。"""
    if (
        config.get("phase") != "comparison"
        or config.get("approved_scope") != "fixed_candidates_offline_only"
    ):
        raise ValueError("仅接受预注册的固定候选离线研究对照")
    plan = ValidationPlan.model_validate(config["validation_plan"])
    history = datasets.load(
        AssetRef.model_validate(config["dataset_ref"]), partition=DatasetPartition.HISTORY
    )
    validation = datasets.load(plan.dataset_ref)
    # 只从清单读取 Final Test 的数量；实际题目在候选和 Gate 结果冻结后加载。
    final_ref = AssetRef.model_validate(config["final_test_ref"])
    final = [
        d
        for d in datasets.manifest.datasets
        if d.ref == final_ref and d.partition == DatasetPartition.FINAL_TEST
    ]
    if len(final) != 1:
        raise ValueError("Final Test 引用未登记或分区错误")
    if len(plan.seeds) != plan.repeats or plan.evaluator_ref != AssetRef(
        id="project-planning-rules", version="1"
    ):
        raise ValueError("采样或评价器配置不匹配")
    return len(history) * 3 + len(validation) * plan.repeats * (6 + 7) + len(final[0].tasks) * 3


def summarize_runs(runs: list[SealedRun]) -> dict[str, Any]:
    metrics = [run.evaluation.metrics for run in runs]
    summary: dict[str, Any] = {
        "total_count": len(runs),
        "success_count": sum(m.success is True for m in metrics),
        "unknown_success_count": sum(m.success is None for m in metrics),
        "latency": Validator._latency([m.latency_seconds for m in metrics]).model_dump(mode="json"),
        "status_counts": {
            status.value: sum(r.status == status for r in runs) for status in RunStatus
        },
    }
    for name in ("tokens", "agent_count", "retry_count", "tool_calls", "hard_constraint_errors"):
        values = [getattr(m, name) for m in metrics]
        summary[name] = sum(values) if values and all(v is not None for v in values) else None
        summary[f"known_{name}_subtotal"] = sum(v for v in values if v is not None)
    return summary


def _write_report(output: Path, report: dict[str, Any]) -> None:
    temporary = output / ".campaign_report.tmp"
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output / "campaign_report.json")


async def execute_campaign(prepared: Any, output: Path, delegate: AgentRuntime) -> dict[str, Any]:
    """使用已保存 preflight 的对象执行；测试可直接注入离线 Runtime。

    对照候选由开发者预先指定，不冒充自动归因产生的候选。Gate 原样调用，
    样本不足不放宽门槛；所有候选仅用于隔离验证，不执行生命周期晋级。
    Final Test 只评估本次未变更的服务策略，不用于筛选候选。
    """
    config, current = prepared.config, prepared.strategy
    datasets = ManifestDatasets(prepared.manifest)
    request_bound = campaign_request_bound(config, datasets)
    if (
        type(config["maximum_model_requests"]) is not int
        or request_bound > config["maximum_model_requests"]
    ):
        raise ValueError("请求上限小于预注册完整批次所需上界")
    if len(current.definition.agents) != 3 or current.definition.orchestration.retry_limit != 0:
        raise ValueError("研究基线必须使用无返工的固定三角色 v0")
    plan = ValidationPlan.model_validate(config["validation_plan"])
    gate_policy = GatePolicy.model_validate(config["gate_policy"])
    monitor_policy = EvolutionPolicy.model_validate(config["monitor_policy"])
    if (output / "evidence.db").exists() or (output / "campaign_report.json").exists():
        raise ValueError("实验输出已存在；禁止覆盖或隐式续跑")
    try:
        with (output / ".execution_started").open("x") as handle:
            handle.write(config["experiment_id"])
    except FileExistsError:
        raise ValueError("实验执行标记已存在；禁止并发或重复执行") from None
    runtime = RequestLimitedRuntime(delegate, maximum_requests=config["maximum_model_requests"])
    storage = SQLiteStorage(f"sqlite:///{output / 'evidence.db'}")
    report: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "status": "running",
        "preflight": prepared.snapshot,
        "mode": "preregistered_research_comparison",
        "serving_before": current.metadata.ref.model_dump(mode="json"),
        "serving_after": current.metadata.ref.model_dump(mode="json"),
        "promoted": None,
        "promotion_eligible": False,
        "promotion_reason": "研究对照不是 Monitor 驱动的自动演进，不改变正式服务版本",
        "comparisons": [],
        "runs": [],
        "snapshots": [],
        "events": [],
        "final_test_run_ids": [],
        "requests_used": 0,
        "limitations": [
            "small_validation_and_final_test_sets",
            "seed_not_applied",
            "no_generalization_claim",
            "research_candidates_not_automatic_evolution",
        ],
    }
    ports = None
    try:
        await storage.initialize()
        if prepared.model is not None:
            await storage.register_model(prepared.model)
        ports = await storage.open()
        await ports.strategies.save(current)
        orchestrator = Orchestrator(runtime, StoreEventSink(ports.runs))
        evaluator = ProjectPlanningEvaluator()
        analyzer = TaskAnalyzer()

        async def execute_partition(
            partition: DatasetPartition, ref: AssetRef, purpose: RunPurpose
        ):
            sealed = []
            for task in datasets.load(ref, partition=partition):
                run = await orchestrator.execute(
                    task, analyzer.analyze(task), current, run_id=str(uuid4()), purpose=purpose
                )
                run.dataset_source = datasets.source_for(task, partition=partition)
                evaluation = await evaluator.evaluate(task, run)
                item = await ports.runs.seal_run(
                    task, run, evaluation, task_scope=task.task_type.value
                )
                sealed.append(item)
                if run.status == RunStatus.CANCELLED:
                    raise asyncio.CancelledError("实验取消；不执行后续任务")
            return sealed

        history = await execute_partition(
            DatasetPartition.HISTORY,
            AssetRef.model_validate(config["dataset_ref"]),
            RunPurpose.ONLINE,
        )
        monitor = StrategyMonitor().inspect(current, history, monitor_policy)
        report["monitor"] = monitor.model_dump(mode="json")
        attributor = OutcomeAttributor(ports.runs)
        history_attribution = await attributor.analyze_failure(history)
        await ports.evolutions.save_attribution(history_attribution)
        report["history_attribution"] = history_attribution.model_dump(mode="json")
        generator = CandidateGenerator()
        # 预先登记的两个单因素研究臂，不用 Validation/Final Test 答案决定候选。
        proposals = (
            MutationProposal(
                proposal_id=f"{config['experiment_id']}-prompt",
                parent=current.metadata.ref,
                operation=MutationType.UPDATE_PROMPT,
                target="executor",
                rationale="预注册研究假设：显式资源检查提示可能减少硬约束错误；尚非自动归因结论",
                attribution_ref=history_attribution.report_id,
                replacement_ref=AssetRef(id="executor", version="v1-resource-check"),
            ),
            MutationProposal(
                proposal_id=f"{config['experiment_id']}-verifier",
                parent=current.metadata.ref,
                operation=MutationType.ADD_AGENT_CONFIG,
                target="verifier",
                rationale="预注册研究假设：独立 Verifier 的质量与成本权衡；尚非自动归因结论",
                attribution_ref=history_attribution.report_id,
                replacement_ref=AssetRef(id="verifier", version="v0"),
            ),
        )
        candidates = []
        for proposal in proposals:
            candidate = generator.materialize(
                current,
                proposal,
                candidate_ref=await ports.strategies.allocate_version(
                    current.metadata.ref.strategy_id
                ),
            )
            await ports.strategies.save(candidate)
            await ports.evolutions.save_proposal(proposal)
            candidates.append((proposal, candidate))
        report["candidate_definitions"] = [c.model_dump(mode="json") for _, c in candidates]
        _write_report(output, report)
        validator = Validator(orchestrator, evaluator, analyzer, ports.runs, datasets)
        for proposal, candidate in candidates:
            validation = await validator.validate(current, candidate, plan)
            await ports.evolutions.save_validation(validation)
            improvement = await attributor.analyze_improvement(validation)
            await ports.evolutions.save_attribution(improvement)
            gate = ValidationGate().decide(validation, improvement, gate_policy)
            report["comparisons"].append(
                {
                    "proposal": proposal.model_dump(mode="json"),
                    "validation": validation.model_dump(mode="json"),
                    "improvement_attribution": improvement.model_dump(mode="json"),
                    "gate": gate.model_dump(mode="json"),
                }
            )
            _write_report(output, report)
        # 所有比较及 Gate 结果先落盘，之后只打开一次 Final Test。
        report["selection_frozen"] = True
        _write_report(output, report)
        final = await execute_partition(
            DatasetPartition.FINAL_TEST,
            AssetRef.model_validate(config["final_test_ref"]),
            RunPurpose.FINAL_TEST,
        )
        report["final_test_run_ids"] = [r.run_id for r in final]
        report["status"] = "completed"
    except BaseException as exc:
        report["status"] = "cancelled" if isinstance(exc, asyncio.CancelledError) else "failed"
        report["termination_reason"] = type(exc).__name__
        raise
    finally:
        try:
            if ports is not None:
                collected = []
                cursor = None
                while True:
                    page, cursor = await ports.runs.list_runs(
                        current.metadata.ref.strategy_id, purpose=None, limit=100, cursor=cursor
                    )
                    collected.extend(page)
                    if cursor is None:
                        break
                report["runs"] = [r.model_dump(mode="json") for r in collected]
                report["snapshots"] = [
                    (await ports.runs.read_snapshot(r.run_id)).model_dump(mode="json")
                    for r in collected
                ]
                report["events"] = [
                    event.model_dump(mode="json")
                    for r in collected
                    for event in await ports.runs.events_for_run(r.run_id)
                ]
                tokens = [r.evaluation.metrics.tokens for r in collected]
                report["total_tokens"] = (
                    sum(t for t in tokens if t is not None)
                    if all(t is not None for t in tokens)
                    else None
                )
                report["known_tokens_subtotal"] = sum(t for t in tokens if t is not None)
                report["cost_minor"] = None
                report["cost_reason"] = "供应商未提供费用；不把缺失用量按零计费"
                report["metrics_by_purpose"] = {
                    p.value: summarize_runs([r for r in collected if r.purpose == p])
                    for p in RunPurpose
                }
                report["purpose_counts"] = {
                    p.value: sum(r.purpose == p for r in collected) for p in RunPurpose
                }
            report["requests_used"] = runtime.requests_used
            _write_report(output, report)
        finally:
            await storage.close()
    return report
