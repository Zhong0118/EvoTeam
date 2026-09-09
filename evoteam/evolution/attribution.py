"""三类归因入口：失败在候选前，贡献跨 Run，改进在验证后。"""

from collections.abc import Sequence

from evoteam.domain.evolution import ValidationResult
from evoteam.domain.experience import AttributionReport
from evoteam.domain.run import SealedRun


class OutcomeAttributor:
    async def analyze_failure(self, runs: Sequence[SealedRun]) -> AttributionReport:
        """P3: 规则 + Trace 定位 Origin / Control；必要时局部 LLM 解释。"""
        raise NotImplementedError("P3: 失败归因尚未实现")

    async def analyze_contribution(self, runs: Sequence[SealedRun]) -> AttributionReport:
        """P3: 以消融/反事实证据衡量节点、工具、边的边际贡献。"""
        raise NotImplementedError("P3: 贡献分析尚未实现")

    async def analyze_improvement(self, result: ValidationResult) -> AttributionReport:
        """P4: 比较验证后解释收益归属、反例与适用范围，再交 Gate。"""
        raise NotImplementedError("P4: 改进归因尚未实现")
