"""三类归因入口：失败在候选前，贡献跨 Run，改进在验证后。"""

from collections.abc import Sequence

from evoteam.domain.evolution import ValidationResult
from evoteam.domain.experience import AttributionClaim, AttributionKind, AttributionReport
from evoteam.domain.run import SealedRun
from evoteam.experience.evidence import evidence_id

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
    async def analyze_failure(self, runs: Sequence[SealedRun]) -> AttributionReport:
        """用已封存的确定性评价定位规划产物 Origin 与审查 Control。"""
        strategy, scope = self._validate_runs(runs)
        failed = tuple(
            run for run in runs if run.evaluation.metrics.success is False or run.evaluation.issues
        )
        refs = tuple(f"run:{run.run_id}" for run in failed)
        issue_codes = {issue.code for run in failed for issue in run.evaluation.issues}
        claims: list[AttributionClaim] = []
        if issue_codes & _PLAN_ISSUES:
            claims.extend(
                (
                    AttributionClaim(
                        kind=AttributionKind.ORIGIN,
                        target="executor",
                        explanation="规则评价发现项目计划产物中的硬约束或 Schema 错误。",
                        confidence=1.0,
                        evidence_refs=refs,
                    ),
                    AttributionClaim(
                        kind=AttributionKind.CONTROL,
                        target="critic",
                        explanation="Critic 位于产物之后，但线上流程仍封存了未通过规则评价的计划。",
                        confidence=0.8,
                        evidence_refs=refs,
                    ),
                )
            )
        elif failed:
            claims.append(
                AttributionClaim(
                    kind=AttributionKind.ORIGIN,
                    target="executor",
                    explanation="Run 失败但现有封存证据不足以定位更细的产生环节。",
                    confidence=0.4,
                    evidence_refs=refs,
                )
            )
        report_id = evidence_id(
            "failure-attribution",
            [strategy.model_dump(), scope, [run.run_id for run in runs], sorted(issue_codes)],
        )
        return AttributionReport(
            report_id=report_id,
            strategy=strategy,
            task_scope=scope,
            claims=tuple(claims),
            needs_more_evidence=not claims or max(claim.confidence for claim in claims) < 0.5,
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
        evidence = (f"validation:{result.validation_id}",)
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
        comparable = bool(parts)
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
