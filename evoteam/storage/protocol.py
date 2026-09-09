"""存储端口；数据库细节不能进入业务控制器。"""

from typing import Protocol

from evoteam.domain.common import StrategyRef
from evoteam.domain.evaluation import EvaluationResult
from evoteam.domain.events import TraceEvent
from evoteam.domain.evolution import EvolutionRecord
from evoteam.domain.run import RunPurpose, RunResult, RunSnapshot, SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task


class RunStore(Protocol):
    async def read_snapshot(self, run_id: str) -> RunSnapshot: ...
    async def events_for_run(self, run_id: str) -> tuple[TraceEvent, ...]: ...
    async def append_event(self, event: TraceEvent) -> None: ...
    async def seal_run(
        self,
        task: Task,
        run: RunResult,
        evaluation: EvaluationResult,
        *,
        task_scope: str,
    ) -> SealedRun:
        """原子保存 Task/Run 快照、评价及封存索引后返回，不能只构造索引。

        P1 Repository 实现应拒绝覆盖封存数据，保留失败与取消，产生封存事件。
        """
        ...

    async def save_sealed_run(self, run: SealedRun) -> None: ...
    async def recent_runs(
        self, strategy: StrategyRef, *, task_scope: str, purpose: RunPurpose, limit: int
    ) -> tuple[SealedRun, ...]: ...


class StrategyStore(Protocol):
    async def get(self, ref: StrategyRef) -> Strategy: ...
    async def save(self, strategy: Strategy) -> None: ...
    async def current(self, strategy_id: str) -> Strategy: ...
    async def allocate_version(self, strategy_id: str) -> StrategyRef: ...
    async def apply_lifecycle(
        self,
        *,
        expected_current: StrategyRef,
        updated_versions: tuple[Strategy, ...],
        serving: StrategyRef,
        record: EvolutionRecord,
    ) -> None:
        """事务写入状态、当前指针和治理记录；校验父版本，防止并发覆盖。"""
        ...


class EvolutionStore(Protocol):
    async def save_record(self, record: EvolutionRecord) -> None: ...
    async def get_record(self, evolution_id: str) -> EvolutionRecord: ...
