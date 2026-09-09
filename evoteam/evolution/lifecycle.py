"""Strategy 生命周期服务；状态修改必须与审计及当前指针一致落盘。"""

from evoteam.domain.common import StrategyRef
from evoteam.domain.evolution import EvolutionRecord, GateResult
from evoteam.domain.strategy import StrategyStatus
from evoteam.storage.protocol import StrategyStore


class StrategyLifecycle:
    def __init__(self, store: StrategyStore) -> None:
        self.store = store

    async def promote(
        self, candidate: StrategyRef, gate: GateResult, record: EvolutionRecord
    ) -> None:
        """P4: 检查 PASS 与父版本，原子切换服务指针并保留旧快照。"""
        raise NotImplementedError("P4: Promote 尚未实现")

    async def reject(
        self, candidate: StrategyRef, gate: GateResult, record: EvolutionRecord
    ) -> None:
        """P4: 拒绝未上线候选，保留负面证据，Current 保持可用。"""
        raise NotImplementedError("P4: Reject 尚未实现")

    async def transition(
        self, strategy: StrategyRef, target: StrategyStatus, record: EvolutionRecord
    ) -> None:
        """P4: 校验合法的 Stable/Reopen 状态转换，不提供任意状态赋值。"""
        raise NotImplementedError("P4: Stable/Reopen 尚未实现")

    async def rollback(
        self, failed: StrategyRef, restore: StrategyRef, record: EvolutionRecord
    ) -> None:
        """P4: 记录退化版本，恢复历史可用版本；区别于 Reject。"""
        raise NotImplementedError("P4: Rollback 尚未实现")
