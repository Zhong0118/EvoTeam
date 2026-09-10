"""三类归因入口：失败在候选前，贡献跨 Run，改进在验证后。"""

from collections.abc import Sequence

from evoteam.domain.evolution import ValidationResult
from evoteam.domain.experience import AttributionClaim, AttributionKind, AttributionReport
from evoteam.domain.planning import PLAN_SCHEMA, REVIEW_SCHEMA, PlanningReview
from evoteam.domain.role import RoleType
from evoteam.domain.run import SealedRun
from evoteam.experience.evidence import evidence_id
from evoteam.storage.protocol import RunStore
from evoteam.tools.constraint_checker import ConstraintChecker

_PLAN_ISSUES = frozenset(
    {
        "output_schema",
        "duplicate_work",
        "missing_work",
        "unknown_work",
        "duration_mismatch",
        "dependency_order",
        "missing_skill",
        "unknown_person",
        "outside_availability",
        "project_deadline",
        "resource_conflict",
        "budget_exceeded",
        "invalid_milestone",
        "missing_milestone",
        "milestone_completion",
        "milestone_deadline",
        "missing_or_ambiguous_plan",
    }
)


class OutcomeAttributor:
    def __init__(self, runs: RunStore | None = None) -> None:
        self.runs = runs

    async def analyze_failure(self, runs: Sequence[SealedRun]) -> AttributionReport:
        """索引只标识失败；用最终产物与实际审查结果确认 Origin / Control。"""
        strategy, scope = self._validate_runs(runs)
        support: dict[tuple[AttributionKind, str], list[str]] = {}
        for sealed in runs:
            if self.runs is None or not any(
                issue.severity == "error" and issue.code in _PLAN_ISSUES
                for issue in sealed.evaluation.issues
            ):
                continue
            try:
                snapshot = await self.runs.read_snapshot(sealed.run_id)
            except KeyError:
                continue
            run = snapshot.run
            if (
                run.run_id != sealed.run_id
                or run.strategy != strategy
                or snapshot.strategy.metadata.ref != strategy
            ):
                raise ValueError("归因快照与封存索引不一致")
            if run.team is None:
                continue
            instances = {instance.instance_id: instance for instance in run.team.instances}
            plans = [result for result in run.results if result.output_schema == PLAN_SCHEMA]
            if not plans:
                continue
            plan = plans[-1]
            executor = instances.get(plan.instance_id)
            if executor is None or executor.config.role != RoleType.EXECUTOR:
                continue
            errors = ConstraintChecker().check(snapshot.task, plan.output)
            if not any(issue.severity == "error" for issue in errors):
                continue
            evidence_ref = f"run:{sealed.run_id}/result:{plan.instance_id}"
            support.setdefault((AttributionKind.ORIGIN, executor.config.node_id), []).append(
                evidence_ref
            )
            # 仅最终计划之后完成、并明确报告通过的 Critic 构成漏检证据。
            # 未执行、超时、或已指出问题不能被归为漏检。
            for result in reversed(run.results):
                if result is plan:
                    break
                critic = instances.get(result.instance_id)
                if (
                    critic is None
                    or critic.config.role != RoleType.CRITIC
                    or result.output_schema != REVIEW_SCHEMA
                ):
                    continue
                review = PlanningReview.model_validate(result.output)
                if review.passed and not review.issues:
                    support.setdefault((AttributionKind.CONTROL, critic.config.node_id), []).append(
                        f"run:{sealed.run_id}/result:{result.instance_id}"
                    )
                break
        claims = tuple(
            AttributionClaim(
                kind=kind,
                target=target,
                explanation=(
                    "最终 Executor 产物经确定性检查仍存在硬约束错误；不推断更深层根因。"
                    if kind == AttributionKind.ORIGIN
                    else "最终产物存在硬约束错误，但其后 Critic 明确报告通过且没有问题。"
                ),
                confidence=1.0,
                evidence_refs=tuple(refs),
            )
            for (kind, target), refs in support.items()
        )
        return AttributionReport(
            report_id=evidence_id(
                "failure-attribution",
                [
                    strategy.model_dump(),
                    scope,
                    [run.run_id for run in runs],
                    [claim.model_dump() for claim in claims],
                ],
            ),
            strategy=strategy,
            task_scope=scope,
            claims=claims,
            needs_more_evidence=not claims,
        )

    async def analyze_contribution(self, runs: Sequence[SealedRun]) -> AttributionReport:
        """没有消融证据时明确返回待采样，避免以发言量冒充贡献。"""
        strategy, scope = self._validate_runs(runs)
        return AttributionReport(
            report_id=evidence_id(
                "contribution-attribution",
                [strategy.model_dump(), scope, [run.run_id for run in runs]],
            ),
            strategy=strategy,
            task_scope=scope,
            claims=(),
            needs_more_evidence=True,
        )

    async def analyze_improvement(self, result: ValidationResult) -> AttributionReport:
        """把配对验证的可观测差值归到当前单因素候选。"""
        current = result.current_metrics
        candidate = result.candidate_metrics
        evidence = (f"validation:{result.validation_id}",) + tuple(
            f"task:{pair.task_id}/repeat:{pair.repeat_index}/runs:{pair.current_run_id},{pair.candidate_run_id}"
            for pair in result.pairs
        )
        parts: list[str] = []
        if (
            current.hard_constraint_errors is not None
            and candidate.hard_constraint_errors is not None
        ):
            parts.append(
                f"硬约束错误 {current.hard_constraint_errors} → {candidate.hard_constraint_errors}"
            )
        if current.quality is not None and candidate.quality is not None:
            parts.append(f"质量 {current.quality:.4f} → {candidate.quality:.4f}")
        if current.success is not None and candidate.success is not None:
            parts.append(f"全部成功 {current.success} → {candidate.success}")
        regressions = sum(
            pair.current_metrics.success is True and pair.candidate_metrics.success is not True
            for pair in result.pairs
        )
        if result.pairs:
            parts.append(f"逐任务成功退化 {regressions}/{len(result.pairs)}")
        comparable = bool(parts) and bool(result.pairs)
        claim = AttributionClaim(
            kind=AttributionKind.IMPROVEMENT,
            target=f"strategy:{result.candidate.strategy_id}@{result.candidate.version}",
            explanation="；".join(parts) if parts else "缺少可比较的质量与约束指标。",
            confidence=1.0 if comparable else 0.0,
            evidence_refs=evidence,
        )
        return AttributionReport(
            report_id=evidence_id("improvement-attribution", [result.model_dump()]),
            strategy=result.candidate,
            task_scope=result.plan.dataset_ref.id,
            claims=(claim,),
            needs_more_evidence=not comparable,
        )

    @staticmethod
    def _validate_runs(runs: Sequence[SealedRun]):
        if not runs:
            raise ValueError("归因至少需要一个封存 Run")
        strategy = runs[0].strategy
        scope = runs[0].task_scope
        if any(run.strategy != strategy or run.task_scope != scope for run in runs):
            raise ValueError("归因证据必须属于同一策略与任务范围")
        if len({run.run_id for run in runs}) != len(runs):
            raise ValueError("归因证据不能包含重复 Run")
        return strategy, scope
