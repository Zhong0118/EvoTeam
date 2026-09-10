"""预注册的晋级规则；不在这里生成候选或切换当前版本。"""

from typing import Annotated

from pydantic import Field

from evoteam.domain.common import AssetRef, FrozenModel, NonNegativeFloat, Probability
from evoteam.domain.evolution import GateDecision, GateResult, ValidationResult
from evoteam.domain.experience import AttributionKind, AttributionReport


class GatePolicy(FrozenModel):
    ref: AssetRef
    minimum_quality_gain: NonNegativeFloat
    maximum_quality_regression: Probability
    maximum_token_increase: NonNegativeFloat
    maximum_latency_increase: NonNegativeFloat
    minimum_paired_runs: Annotated[int, Field(ge=2)] | None = None
    minimum_independent_tasks: Annotated[int, Field(ge=1)] | None = None
    maximum_subclass_success_regression: Probability | None = None
    # None 保持旧配置可读，但未经样本量预注册不能晋级。
    # TODO(P4): 质量/效率两类 Gate、严重错误、负迁移与置信规则。
    # 无默认门槛；不把示例数字当作校准值。


class ValidationGate:
    def decide(
        self,
        result: ValidationResult,
        improvement: AttributionReport,
        policy: GatePolicy,
    ) -> GateResult:
        """按预注册阈值裁决；指标未知时不把未知当作零或自动 PASS。"""
        if improvement.strategy != result.candidate:
            raise ValueError("改进归因与 Candidate 不匹配")
        if (
            not result.current_run_ids
            or len(result.current_run_ids) != len(result.candidate_run_ids)
            or len(set(result.current_run_ids)) != len(result.current_run_ids)
            or len(set(result.candidate_run_ids)) != len(result.candidate_run_ids)
            or set(result.current_run_ids) & set(result.candidate_run_ids)
        ):
            raise ValueError("Gate 只接受非空配对验证")
        if not any(
            claim.kind == AttributionKind.IMPROVEMENT
            and f"validation:{result.validation_id}" in claim.evidence_refs
            for claim in improvement.claims
        ):
            raise ValueError("改进归因没有引用本次 Validation")
        if result.pairs and (
            tuple(pair.current_run_id for pair in result.pairs) != result.current_run_ids
            or tuple(pair.candidate_run_id for pair in result.pairs) != result.candidate_run_ids
            or len({(pair.task_fingerprint, pair.repeat_index) for pair in result.pairs})
            != len(result.pairs)
        ):
            raise ValueError("ValidationPair 与有序 Run 索引不一致或包含重复任务重复次序")
        missing_evidence = False
        reasons: list[str] = []
        failures: list[str] = []
        if (
            policy.minimum_paired_runs is None
            or len(result.current_run_ids) < policy.minimum_paired_runs
        ):
            missing_evidence = True
            reasons.append("配对样本门槛未登记或样本不足")
        if not result.pairs:
            missing_evidence = True
            reasons.append("缺少逐任务 ValidationPair；旧聚合记录不能作为完整配对证据")
        independent_tasks = len({pair.task_fingerprint for pair in result.pairs})
        if (
            policy.minimum_independent_tasks is None
            or independent_tasks < policy.minimum_independent_tasks
        ):
            missing_evidence = True
            reasons.append(f"独立任务数={independent_tasks}，门槛未登记或样本不足")
        if policy.maximum_subclass_success_regression is None:
            missing_evidence = True
            reasons.append("子类成功率退化边界未登记")
        elif result.pairs:
            for subclass in sorted({pair.subclass for pair in result.pairs}):
                members = [pair for pair in result.pairs if pair.subclass == subclass]
                before = [pair.current_metrics.success for pair in members]
                after = [pair.candidate_metrics.success for pair in members]
                if any(value is None for value in before + after):
                    missing_evidence = True
                    reasons.append(f"子类 {subclass} 存在未知成功状态")
                    continue
                regression = sum(value is True for value in before) / len(before) - sum(
                    value is True for value in after
                ) / len(after)
                reasons.append(f"子类 {subclass} 成功率退化={regression:.6f}")
                if regression > policy.maximum_subclass_success_regression:
                    failures.append(f"子类 {subclass} 成功率退化超过允许上限")
        for pair in result.pairs:
            if pair.current_metrics.success is True and pair.candidate_metrics.success is not True:
                failures.append(
                    f"任务 {pair.task_id} repeat={pair.repeat_index} 从成功退化为失败或未知"
                )
            before_errors = pair.current_metrics.hard_constraint_errors
            after_errors = pair.candidate_metrics.hard_constraint_errors
            if (
                before_errors is not None
                and after_errors is not None
                and after_errors > before_errors
            ):
                failures.append(
                    f"任务 {pair.task_id} repeat={pair.repeat_index} 引入更多硬约束错误"
                )
        current = result.current_metrics
        candidate = result.candidate_metrics

        if current.success is True and candidate.success is not True:
            failures.append("Candidate 将全部成功退化为存在失败")
        if (
            current.hard_constraint_errors is not None
            and candidate.hard_constraint_errors is not None
            and candidate.hard_constraint_errors > current.hard_constraint_errors
        ):
            failures.append("Candidate 引入了更多硬约束错误")

        quality_improved = False
        if current.quality is not None and candidate.quality is not None:
            delta = candidate.quality - current.quality
            reasons.append(f"质量差值={delta:.6f}")
            if delta < -policy.maximum_quality_regression:
                failures.append("质量退化超过允许上限")
            quality_improved = delta > 0 and delta >= policy.minimum_quality_gain

        constraint_improved = (
            current.hard_constraint_errors is not None
            and candidate.hard_constraint_errors is not None
            and candidate.hard_constraint_errors < current.hard_constraint_errors
        )
        success_improved = current.success is False and candidate.success is True
        for label, before, after, limit in (
            ("Token", current.tokens, candidate.tokens, policy.maximum_token_increase),
            (
                "延迟",
                current.latency_seconds,
                candidate.latency_seconds,
                policy.maximum_latency_increase,
            ),
        ):
            if before is None or after is None:
                missing_evidence = True
                reasons.append(f"{label}指标未知")
                continue
            increase = self._relative_increase(float(before), float(after))
            reasons.append(f"{label}相对增幅={increase:.6f}")
            if increase > limit:
                failures.append(f"{label}增幅超过允许上限")

        if failures:
            decision = GateDecision.FAIL
            reasons.extend(failures)
        elif improvement.needs_more_evidence or missing_evidence:
            decision = GateDecision.CONTINUE_SAMPLING
            reasons.append("改进归因缺少可比较证据")
        elif not (quality_improved or constraint_improved or success_improved):
            decision = GateDecision.FAIL
            reasons.append("Candidate 未达到任何预注册的正向收益条件")
        else:
            decision = GateDecision.PASS
            reasons.append("质量/硬约束收益满足条件且未触发回归边界")
        return GateResult(
            validation_id=result.validation_id,
            decision=decision,
            policy_ref=policy.ref,
            reasons=tuple(reasons),
            improvement_attribution_ref=improvement.report_id,
        )

    @staticmethod
    def _relative_increase(before: float, after: float) -> float:
        if after <= before:
            return 0.0
        if before == 0:
            return float("inf")
        return (after - before) / before
