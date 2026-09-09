"""预注册的晋级规则；不在这里生成候选或切换当前版本。"""

from evoteam.domain.common import AssetRef, FrozenModel, NonNegativeFloat, Probability
from evoteam.domain.evolution import GateDecision, GateResult, ValidationResult
from evoteam.domain.experience import AttributionReport


class GatePolicy(FrozenModel):
    ref: AssetRef
    minimum_quality_gain: NonNegativeFloat
    maximum_quality_regression: Probability
    maximum_token_increase: NonNegativeFloat
    maximum_latency_increase: NonNegativeFloat
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
        if not result.current_run_ids or len(result.current_run_ids) != len(
            result.candidate_run_ids
        ):
            raise ValueError("Gate 只接受非空配对验证")
        reasons: list[str] = []
        failures: list[str] = []
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
            quality_improved = delta >= policy.minimum_quality_gain

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
                reasons.append(f"{label}指标未知")
                continue
            increase = self._relative_increase(float(before), float(after))
            reasons.append(f"{label}相对增幅={increase:.6f}")
            if increase > limit:
                failures.append(f"{label}增幅超过允许上限")

        if failures:
            decision = GateDecision.FAIL
            reasons.extend(failures)
        elif improvement.needs_more_evidence:
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
