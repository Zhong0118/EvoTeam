"""独立批量实验器；比较执行不等同于 Gate 判定。"""

from evoteam.domain.evolution import ValidationPlan, ValidationResult
from evoteam.domain.strategy import Strategy
from evoteam.evaluation.evaluator import Evaluator
from evoteam.orchestration.orchestrator import Orchestrator


class Validator:
    def __init__(self, orchestrator: Orchestrator, evaluator: Evaluator) -> None:
        self.orchestrator = orchestrator
        self.evaluator = evaluator

    async def validate(
        self,
        current: Strategy,
        candidate: Strategy,
        plan: ValidationPlan,
    ) -> ValidationResult:
        """P4: 同任务/模型/工具/预算，反复调用执行与评分，汇总分布。

        RunPurpose 固定 VALIDATION，不混入 online 窗口；保留失败与成本。
        """
        raise NotImplementedError("P4: 独立验证实验尚未实现")
