"""存储端口；数据库细节不能进入业务控制器。"""

from typing import Protocol

from evoteam.domain.common import StrategyRef
from evoteam.domain.evaluation import EvaluationResult
from evoteam.domain.events import TraceEvent
from evoteam.domain.evolution import EvolutionRecord, MutationProposal, ValidationResult
from evoteam.domain.experience import AttributionReport
from evoteam.domain.run import RunPurpose, RunResult, RunSnapshot, SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task


class RunStore(Protocol):
    async def get_sealed_run(self, run_id: str) -> SealedRun: ...
    async def list_runs(
        self,
        strategy_id: str,
        *,
        purpose: RunPurpose | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[tuple[SealedRun, ...], str | None]: ...
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

        必须保存 run.dataset_source 原始执行来源，不得用当前清单回填。
        P1 Repository 实现应拒绝覆盖封存数据，保留失败与取消，产生封存事件。
        """
        ...

    async def save_sealed_run(self, run: SealedRun) -> None: ...
    async def recent_runs(
        self, strategy: StrategyRef, *, task_scope: str, purpose: RunPurpose, limit: int
    ) -> tuple[SealedRun, ...]: ...


class StrategyStore(Protocol):
    async def abort_candidates(self, record: EvolutionRecord) -> None:
        """只拒绝尚未服务的候选并保存终止记录，不修改当前服务指针。"""
        ...

    async def get(self, ref: StrategyRef) -> Strategy: ...
    async def list_versions(self, strategy_id: str) -> tuple[Strategy, ...]: ...
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
    async def claim(
        self, evolution_id: str, strategy: StrategyRef, request_fingerprint: str
    ) -> EvolutionRecord | None:
        """原子消费 Trigger；已完成返回记录，进行中拒绝，首次成功返回 None。"""
        ...

    async def save_attribution(self, report: AttributionReport) -> None: ...
    async def get_attribution(self, report_id: str) -> AttributionReport: ...
    async def save_proposal(self, proposal: MutationProposal) -> None: ...
    async def get_proposal(self, proposal_id: str) -> MutationProposal: ...
    async def save_validation(self, result: ValidationResult) -> None: ...
    async def get_validation(self, validation_id: str) -> ValidationResult: ...
    async def save_record(self, record: EvolutionRecord) -> None: ...
    async def get_record(self, evolution_id: str) -> EvolutionRecord: ...
    async def list_records(
        self, strategy_id: str, *, limit: int, cursor: str | None
    ) -> tuple[tuple[EvolutionRecord, ...], str | None]: ...
