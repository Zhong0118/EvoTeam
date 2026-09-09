"""预注册的晋级规则；不在这里生成候选或切换当前版本。"""

from evoteam.domain.common import AssetRef, FrozenModel, NonNegativeFloat, Probability
from evoteam.domain.evolution import GateResult, ValidationResult
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
        """P4: 输出 PASS/FAIL/CONTINUE_SAMPLING/NARROW_SCOPE 及证据。"""
        raise NotImplementedError("P4: Validation Gate 尚未实现")
