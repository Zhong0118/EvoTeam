"""经验持久化端口，保存与聚合分离；不是一个业务 Agent。"""

from typing import Protocol

from evoteam.domain.common import StrategyRef
from evoteam.domain.experience import FailureExperience, ImprovementExperience, OutcomePattern


class ExperienceStore(Protocol):
    async def save_failure(self, experience: FailureExperience) -> None: ...
    async def save_improvement(self, experience: ImprovementExperience) -> None: ...
    async def save_pattern(self, pattern: OutcomePattern) -> None: ...
    async def list_patterns(
        self,
        strategy: StrategyRef,
        *,
        task_scope: str,
    ) -> tuple[OutcomePattern, ...]: ...
