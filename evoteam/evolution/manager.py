"""只有 Trigger 后启动的离线总控；不亲自打分或决定 Gate。"""

from collections.abc import Sequence

from evoteam.domain.evolution import EvolutionRecord, EvolutionTrigger, ValidationPlan
from evoteam.domain.run import SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.gate import GatePolicy, ValidationGate
from evoteam.evolution.lifecycle import StrategyLifecycle
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import Validator
from evoteam.monitoring.policy import EvolutionPolicy


class EvolutionManager:
    def __init__(
        self,
        attributor: OutcomeAttributor,
        generator: CandidateGenerator,
        validator: Validator,
        gate: ValidationGate,
        lifecycle: StrategyLifecycle,
    ) -> None:
        self.attributor = attributor
        self.generator = generator
        self.validator = validator
        self.gate = gate
        self.lifecycle = lifecycle

    async def evolve(
        self,
        trigger: EvolutionTrigger,
        current: Strategy,
        evidence: Sequence[SealedRun],
        policy: EvolutionPolicy,
        validation_plan: ValidationPlan,
        gate_policy: GatePolicy,
    ) -> EvolutionRecord:
        """P3/P4: 校验 Trigger → 归因 → 候选 → 实验 → 改进归因 → Gate → 生命周期。

        后续注入版本分配器与治理存储；重复 Trigger、预算耗尽、异常都要记录。
        CandidateGenerator 不接收 validation_plan 或验证答案。
        """
        raise NotImplementedError("P3/P4: 离线演进流程尚未实现")
