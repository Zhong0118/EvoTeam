"""独立批量实验器；比较执行不等同于 Gate 判定。"""

from statistics import fmean
from typing import Protocol
from uuid import uuid4

from evoteam.domain.evaluation import RunMetrics
from evoteam.domain.evolution import ValidationPlan, ValidationResult
from evoteam.domain.run import RunPurpose, RunStatus
from evoteam.domain.strategy import Strategy
from evoteam.evaluation.evaluator import Evaluator
from evoteam.evolution.datasets import ValidationDatasetProvider
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.storage.protocol import RunStore


class ValidationRunner(Protocol):
    async def validate(
        self, current: Strategy, candidate: Strategy, plan: ValidationPlan
    ) -> ValidationResult: ...


class Validator:
    def __init__(
        self,
        orchestrator: Orchestrator,
        evaluator: Evaluator,
        analyzer: TaskAnalyzer,
        runs: RunStore,
        datasets: ValidationDatasetProvider,
    ) -> None:
        self.orchestrator = orchestrator
        self.evaluator = evaluator
        self.analyzer = analyzer
        self.runs = runs
        self.datasets = datasets

    async def validate(
        self,
        current: Strategy,
        candidate: Strategy,
        plan: ValidationPlan,
    ) -> ValidationResult:
        """在同一数据集上配对执行 Current/Candidate，评价并封存。

        RunPurpose 固定 VALIDATION，不混入 online 窗口；保留失败与成本。
        """
        if current.metadata.ref != candidate.metadata.parent:
            raise ValueError("Candidate 必须直接来源于本次 Current")
        if plan.evaluator_ref.id != "project-planning-rules":
            raise ValueError("ValidationPlan 的 evaluator_ref 与当前 Evaluator 不匹配")
        tasks = self.datasets.load(plan.dataset_ref)
        if not tasks:
            raise ValueError("验证集不能为空")
        if len(plan.seeds) != plan.repeats:
            raise ValueError("首版要求每次重复提供一个明确 seed")

        current_run_ids: list[str] = []
        candidate_run_ids: list[str] = []
        current_metrics: list[RunMetrics] = []
        candidate_metrics: list[RunMetrics] = []
        for repeat, _seed in enumerate(plan.seeds):
            for task in tasks:
                for selected, ids, metrics in (
                    (current, current_run_ids, current_metrics),
                    (candidate, candidate_run_ids, candidate_metrics),
                ):
                    run_id = f"validation-{repeat}-{uuid4()}"
                    task_copy = task.model_copy(deep=True)
                    run = await self.orchestrator.execute(
                        task_copy,
                        self.analyzer.analyze(task_copy),
                        selected,
                        run_id=run_id,
                        purpose=RunPurpose.VALIDATION,
                    )
                    if run.status not in {
                        RunStatus.COMPLETED,
                        RunStatus.FAILED,
                        RunStatus.TIMED_OUT,
                        RunStatus.CANCELLED,
                    }:
                        raise ValueError("验证 Run 未终结")
                    evaluation = await self.evaluator.evaluate(task_copy, run)
                    if evaluation.evaluator_ref != plan.evaluator_ref:
                        raise ValueError("实际 Evaluator 与预注册 ValidationPlan 不一致")
                    sealed = await self.runs.seal_run(
                        task_copy, run, evaluation, task_scope=task_copy.task_type.value
                    )
                    ids.append(sealed.run_id)
                    metrics.append(sealed.evaluation.metrics)

        validation_id = str(uuid4())
        return ValidationResult(
            validation_id=validation_id,
            current=current.metadata.ref,
            candidate=candidate.metadata.ref,
            plan=plan,
            current_run_ids=tuple(current_run_ids),
            candidate_run_ids=tuple(candidate_run_ids),
            current_metrics=self._aggregate(current_metrics),
            candidate_metrics=self._aggregate(candidate_metrics),
        )

    @staticmethod
    def _aggregate(values: list[RunMetrics]) -> RunMetrics:
        if not values:
            raise ValueError("不能汇总空验证结果")

        def mean(field: str) -> float | None:
            known = [getattr(value, field) for value in values]
            return fmean(known) if all(item is not None for item in known) else None

        def total(field: str) -> int | None:
            known = [getattr(value, field) for value in values]
            return sum(known) if all(item is not None for item in known) else None

        success = [value.success for value in values]
        return RunMetrics(
            quality=mean("quality"),
            success=all(success) if all(item is not None for item in success) else None,
            hard_constraint_errors=total("hard_constraint_errors"),
            tokens=total("tokens"),
            cost=mean("cost"),
            latency_seconds=mean("latency_seconds"),
            agent_count=total("agent_count"),
            tool_calls=total("tool_calls"),
            retry_count=total("retry_count"),
        )
