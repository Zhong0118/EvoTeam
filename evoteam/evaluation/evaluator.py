"""独立程序评价；只定义硬约束通过，不冒充综合质量评分。"""

from typing import Protocol

from evoteam.domain.common import AssetRef
from evoteam.domain.evaluation import EvaluationIssue, EvaluationResult
from evoteam.domain.planning import PLAN_SCHEMA, parse_planning_task
from evoteam.domain.run import RunResult, RunStatus
from evoteam.domain.task import Task
from evoteam.evaluation.metrics import MetricsCollector
from evoteam.tools.constraint_checker import ConstraintChecker


class Evaluator(Protocol):
    async def evaluate(self, task: Task, run: RunResult) -> EvaluationResult: ...


class ProjectPlanningEvaluator:
    async def evaluate(self, task: Task, run: RunResult) -> EvaluationResult:
        parse_planning_task(task)
        if run.task_id != task.task_id:
            raise ValueError("评价任务与 Run 不匹配")
        plans = [r for r in run.results if r.output_schema == PLAN_SCHEMA]
        if plans:
            # 有界返工会保留旧产物作为证据；最终一次 Executor 产物才是交付结果。
            issues = ConstraintChecker().check(task, plans[-1].output)
        else:
            issues = (
                EvaluationIssue(
                    code="missing_or_ambiguous_plan",
                    message="需要唯一的项目计划产物",
                    severity="error",
                    evidence_refs=(f"run:{run.run_id}/results",),
                ),
            )
        metrics = (
            MetricsCollector()
            .collect(run)
            .model_copy(
                update={
                    "success": run.status == RunStatus.COMPLETED and not issues,
                    "hard_constraint_errors": len(issues),
                }
            )
        )
        return EvaluationResult(
            run_id=run.run_id,
            evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
            metrics=metrics,
            issues=issues,
            missing_metrics=tuple(
                key for key, value in metrics.model_dump().items() if value is None
            ),
        )
