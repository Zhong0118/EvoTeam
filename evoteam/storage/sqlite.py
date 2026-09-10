"""单机 SQLite 在线证据存储；显式建表，短事务同步执行，未用于高并发服务。"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import JsonValue
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
    select,
)
from sqlalchemy.engine import Engine

from evoteam.domain.common import StrategyRef
from evoteam.domain.evaluation import EvaluationResult
from evoteam.domain.events import EventType, TraceEvent
from evoteam.domain.evolution import EvolutionRecord, MutationProposal, ValidationResult
from evoteam.domain.experience import (
    AttributionReport,
    FailureExperience,
    ImprovementExperience,
    OutcomePattern,
)
from evoteam.domain.run import RunPurpose, RunResult, RunSnapshot, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task
from evoteam.experience.store import ExperienceStore
from evoteam.monitoring.state import MonitorState, MonitorStore
from evoteam.runtime.models import ModelEndpoint
from evoteam.storage.protocol import EvolutionStore, RunStore, StrategyStore

metadata = MetaData()
model_configs = Table(
    "model_configs",
    metadata,
    Column("model_id", String, primary_key=True),
    Column("version", String, primary_key=True),
    Column("data", Text, nullable=False),
)
experiences = Table(
    "experiences",
    metadata,
    Column("record_id", String, primary_key=True),
    Column("kind", String, nullable=False),
    Column("strategy_id", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("scope", String, nullable=False),
    Column("data", Text, nullable=False),
)
monitor_states = Table(
    "monitor_states",
    metadata,
    Column("key", String, primary_key=True),
    Column("revision", Integer, nullable=False),
    Column("data", Text, nullable=False),
)
strategies = Table(
    "strategies",
    metadata,
    Column("strategy_id", String, primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("serving_id", String, unique=True),
    Column("data", Text, nullable=False),
)
strategy_counters = Table(
    "strategy_counters",
    metadata,
    Column("strategy_id", String, primary_key=True),
    Column("last_version", Integer, nullable=False),
)
evolutions = Table(
    "evolutions",
    metadata,
    Column("evolution_id", String, primary_key=True),
    Column("strategy_id", String, nullable=False),
    Column("data", Text, nullable=False),
)
evolution_claims = Table(
    "evolution_claims",
    metadata,
    Column("evolution_id", String, primary_key=True),
    Column("request_fingerprint", String, nullable=False),
    Column("active_strategy_id", String, unique=True),
)
attributions = Table(
    "attributions",
    metadata,
    Column("report_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)
mutation_proposals = Table(
    "mutation_proposals",
    metadata,
    Column("proposal_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)
validations = Table(
    "validations",
    metadata,
    Column("validation_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)
runs = Table(
    "runs",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("strategy_id", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("scope", String, nullable=False),
    Column("purpose", String, nullable=False),
    Column("sealed_at", String, nullable=False),
    Column("snapshot", Text, nullable=False),
    Column("sealed", Text, nullable=False),
)
events = Table(
    "events",
    metadata,
    Column("event_id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("data", Text, nullable=False),
    UniqueConstraint("run_id", "sequence"),
)


@dataclass(frozen=True)
class StoragePorts:
    runs: RunStore
    strategies: StrategyStore
    experiences: ExperienceStore
    evolutions: EvolutionStore
    monitoring: MonitorStore | None = None


class SQLiteRunStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    async def append_event(self, event: TraceEvent) -> None:
        if event.run_id is None or event.task_id is None:
            raise ValueError("在线事件必须关联 Run 和 Task")
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            if conn.execute(select(runs.c.run_id).where(runs.c.run_id == event.run_id)).first():
                raise ValueError("封存后不能追加事件")
            history = (
                conn.execute(
                    select(events.c.data)
                    .where(events.c.run_id == event.run_id)
                    .order_by(events.c.sequence)
                )
                .scalars()
                .all()
            )
            if event.sequence != len(history):
                raise ValueError("事件序号必须连续")
            if history:
                first = TraceEvent.model_validate_json(history[0])
                if first.task_id != event.task_id or first.strategy != event.strategy:
                    raise ValueError("事件身份与已有 Run 不匹配")
            conn.execute(
                events.insert().values(
                    event_id=event.event_id,
                    run_id=event.run_id,
                    sequence=event.sequence,
                    data=event.model_dump_json(),
                )
            )

    async def seal_run(
        self, task: Task, run: RunResult, evaluation: EvaluationResult, *, task_scope: str
    ) -> SealedRun:
        if (
            task.task_id != run.task_id
            or evaluation.run_id != run.run_id
            or task_scope != task.task_type.value
            or run.status
            not in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.TIMED_OUT}
        ):
            raise ValueError("封存身份或状态不合法")
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            if conn.execute(select(runs.c.run_id).where(runs.c.run_id == run.run_id)).first():
                raise ValueError("不能覆盖封存 Run")
            strategy_json = conn.execute(
                select(strategies.c.data).where(
                    strategies.c.strategy_id == run.strategy.strategy_id,
                    strategies.c.version == run.strategy.version,
                )
            ).scalar_one()
            strategy = Strategy.model_validate_json(strategy_json)
            if run.team and run.team.strategy != run.strategy:
                raise ValueError("Team 策略身份不匹配")
            trace = [
                TraceEvent.model_validate_json(value)
                for value in conn.execute(
                    select(events.c.data)
                    .where(events.c.run_id == run.run_id)
                    .order_by(events.c.sequence)
                ).scalars()
            ]
            if (
                tuple(event.event_id for event in trace) != run.trace_refs
                or not trace
                or any(
                    event.task_id != task.task_id or event.strategy != run.strategy
                    for event in trace
                )
                or trace[-1].event_type != EventType.RUN_FINISHED
            ):
                raise ValueError("必须封存与 Run 对应的完整终结 Trace")
            now = datetime.now(UTC)
            final_events: tuple[tuple[EventType, dict[str, JsonValue]], ...] = (
                (
                    EventType.EVALUATION_COMPLETED,
                    {"evaluation": evaluation.model_dump(mode="json")},
                ),
                (EventType.RUN_SEALED, {"snapshot_ref": f"sqlite:run:{run.run_id}"}),
            )
            for kind, payload in final_events:
                event = TraceEvent(
                    event_id=str(uuid4()),
                    event_type=kind,
                    timestamp=now,
                    sequence=len(trace),
                    run_id=run.run_id,
                    task_id=task.task_id,
                    strategy=run.strategy,
                    caused_by=(trace[-1].event_id,),
                    payload=payload,
                )
                conn.execute(
                    events.insert().values(
                        event_id=event.event_id,
                        run_id=run.run_id,
                        sequence=event.sequence,
                        data=event.model_dump_json(),
                    )
                )
                trace.append(event)
            sealed = SealedRun(
                run_id=run.run_id,
                task_id=task.task_id,
                task_scope=task_scope,
                strategy=run.strategy,
                purpose=run.purpose,
                status=run.status,
                sealed_at=now,
                snapshot_ref=f"sqlite:run:{run.run_id}",
                trace_refs=tuple(event.event_id for event in trace),
                evaluation=evaluation,
                output_ref=run.output_ref,
            )
            snapshot = RunSnapshot(task=task, strategy=strategy, run=run)
            conn.execute(
                runs.insert().values(
                    run_id=run.run_id,
                    strategy_id=run.strategy.strategy_id,
                    version=run.strategy.version,
                    scope=task_scope,
                    purpose=run.purpose.value,
                    sealed_at=now.isoformat(),
                    snapshot=snapshot.model_dump_json(),
                    sealed=sealed.model_dump_json(),
                )
            )
        return sealed

    async def save_sealed_run(self, run: SealedRun) -> None:
        # 兼容旧端口；不能绕过 seal_run 写一个没有实际快照的索引。
        with self.engine.connect() as conn:
            value = conn.execute(select(runs.c.sealed).where(runs.c.run_id == run.run_id)).scalar()
        if value is None or SealedRun.model_validate_json(value) != run:
            raise ValueError("必须通过 seal_run 创建完整封存记录")

    async def recent_runs(
        self, strategy: StrategyRef, *, task_scope: str, purpose: RunPurpose, limit: int
    ) -> tuple[SealedRun, ...]:
        if limit <= 0:
            raise ValueError("limit 必须为正")
        with self.engine.connect() as conn:
            values = (
                conn.execute(
                    select(runs.c.sealed)
                    .where(
                        runs.c.strategy_id == strategy.strategy_id,
                        runs.c.version == strategy.version,
                        runs.c.scope == task_scope,
                        runs.c.purpose == purpose.value,
                    )
                    .order_by(runs.c.sealed_at.desc(), runs.c.run_id)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
        return tuple(SealedRun.model_validate_json(value) for value in reversed(values))

    async def read_snapshot(self, run_id: str) -> RunSnapshot:
        with self.engine.connect() as conn:
            value = conn.execute(
                select(runs.c.snapshot).where(runs.c.run_id == run_id)
            ).scalar_one()
        return RunSnapshot.model_validate_json(value)

    async def events_for_run(self, run_id: str) -> tuple[TraceEvent, ...]:
        with self.engine.connect() as conn:
            values = (
                conn.execute(
                    select(events.c.data)
                    .where(events.c.run_id == run_id)
                    .order_by(events.c.sequence)
                )
                .scalars()
                .all()
            )
        return tuple(TraceEvent.model_validate_json(value) for value in values)


class SQLiteStrategyStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    async def abort_candidates(self, record: EvolutionRecord) -> None:
        if record.promoted is not None or record.termination_reason is None:
            raise ValueError("只能终止未晋级的演进")
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            for ref in record.candidates:
                if ref.strategy_id != record.trigger.strategy.strategy_id:
                    raise ValueError("终止候选不能跨 Strategy")
                row = conn.execute(
                    select(strategies.c.data, strategies.c.serving_id).where(
                        strategies.c.strategy_id == ref.strategy_id,
                        strategies.c.version == ref.version,
                    )
                ).one()
                candidate = Strategy.model_validate_json(row.data)
                if row.serving_id is None and candidate.metadata.status in {
                    StrategyStatus.CANDIDATE,
                    StrategyStatus.VALIDATING,
                }:
                    rejected = candidate.model_copy(
                        update={
                            "metadata": candidate.metadata.model_copy(
                                update={"status": StrategyStatus.REJECTED}
                            )
                        }
                    )
                    conn.execute(
                        strategies.update()
                        .where(
                            strategies.c.strategy_id == ref.strategy_id,
                            strategies.c.version == ref.version,
                        )
                        .values(data=rejected.model_dump_json())
                    )
            conn.execute(
                evolutions.insert().values(
                    evolution_id=record.evolution_id,
                    strategy_id=record.trigger.strategy.strategy_id,
                    data=record.model_dump_json(),
                )
            )
            conn.execute(
                evolution_claims.update()
                .where(evolution_claims.c.evolution_id == record.evolution_id)
                .values(active_strategy_id=None)
            )

    async def save(self, strategy: Strategy) -> None:
        """仅首次登记；唯一约束禁止覆盖旧版本或创建第二个 Current。"""
        ref = strategy.metadata.ref
        serving = (
            ref.strategy_id
            if strategy.metadata.status in {StrategyStatus.CURRENT, StrategyStatus.STABLE}
            else None
        )
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            conn.execute(
                strategies.insert().values(
                    strategy_id=ref.strategy_id,
                    version=ref.version,
                    serving_id=serving,
                    data=strategy.model_dump_json(),
                )
            )
            previous = conn.execute(
                select(strategy_counters.c.last_version).where(
                    strategy_counters.c.strategy_id == ref.strategy_id
                )
            ).scalar()
            if previous is None:
                conn.execute(
                    strategy_counters.insert().values(
                        strategy_id=ref.strategy_id, last_version=ref.version
                    )
                )
            elif previous < ref.version:
                conn.execute(
                    strategy_counters.update()
                    .where(strategy_counters.c.strategy_id == ref.strategy_id)
                    .values(last_version=ref.version)
                )

    async def get(self, ref: StrategyRef) -> Strategy:
        with self.engine.connect() as conn:
            value = conn.execute(
                select(strategies.c.data).where(
                    strategies.c.strategy_id == ref.strategy_id, strategies.c.version == ref.version
                )
            ).scalar_one_or_none()
        if value is None:
            raise KeyError(ref)
        return Strategy.model_validate_json(value)

    async def current(self, strategy_id: str) -> Strategy:
        with self.engine.connect() as conn:
            value = conn.execute(
                select(strategies.c.data).where(strategies.c.serving_id == strategy_id)
            ).scalar_one_or_none()
        if value is None:
            raise KeyError(strategy_id)
        return Strategy.model_validate_json(value)

    async def allocate_version(self, strategy_id: str) -> StrategyRef:
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            last = conn.execute(
                select(strategy_counters.c.last_version).where(
                    strategy_counters.c.strategy_id == strategy_id
                )
            ).scalar()
            if last is None:
                raise ValueError("不能为未登记的 Strategy 分配版本")
            next_version = last + 1
            conn.execute(
                strategy_counters.update()
                .where(strategy_counters.c.strategy_id == strategy_id)
                .values(last_version=next_version)
            )
        return StrategyRef(strategy_id=strategy_id, version=next_version)

    async def apply_lifecycle(
        self,
        *,
        expected_current: StrategyRef,
        updated_versions: tuple[Strategy, ...],
        serving: StrategyRef,
        record: EvolutionRecord,
    ) -> None:
        if not updated_versions:
            raise ValueError("生命周期事务至少更新一个版本")
        refs = tuple(item.metadata.ref for item in updated_versions)
        if len(set(refs)) != len(refs):
            raise ValueError("生命周期事务包含重复版本")
        if any(ref.strategy_id != expected_current.strategy_id for ref in refs):
            raise ValueError("生命周期事务不能跨 Strategy")
        if serving.strategy_id != expected_current.strategy_id:
            raise ValueError("服务指针不能跨 Strategy")
        if record.trigger.strategy != expected_current:
            raise ValueError("治理记录 Trigger 与预期 Current 不匹配")
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            serving_row = conn.execute(
                select(strategies.c.version, strategies.c.data).where(
                    strategies.c.serving_id == expected_current.strategy_id
                )
            ).one_or_none()
            if serving_row is None or serving_row.version != expected_current.version:
                raise ValueError("Current 已变化，拒绝陈旧生命周期操作")
            for updated in updated_versions:
                stored_json = conn.execute(
                    select(strategies.c.data).where(
                        strategies.c.strategy_id == updated.metadata.ref.strategy_id,
                        strategies.c.version == updated.metadata.ref.version,
                    )
                ).scalar()
                if stored_json is None:
                    raise ValueError("生命周期目标版本尚未保存")
                stored = Strategy.model_validate_json(stored_json)
                if (
                    stored.definition != updated.definition
                    or stored.metadata.ref != updated.metadata.ref
                    or stored.metadata.parent != updated.metadata.parent
                    or stored.metadata.generation != updated.metadata.generation
                ):
                    raise ValueError("生命周期操作不能改写策略定义或版本谱系")
            if (
                conn.execute(
                    select(strategies.c.version).where(
                        strategies.c.strategy_id == serving.strategy_id,
                        strategies.c.version == serving.version,
                    )
                ).scalar()
                is None
            ):
                raise ValueError("服务目标版本不存在")
            if (
                conn.execute(
                    select(evolutions.c.evolution_id).where(
                        evolutions.c.evolution_id == record.evolution_id
                    )
                ).scalar()
                is not None
            ):
                raise ValueError("EvolutionRecord 已存在，禁止重复应用")
            conn.execute(
                strategies.update()
                .where(strategies.c.strategy_id == expected_current.strategy_id)
                .values(serving_id=None)
            )
            for updated in updated_versions:
                ref = updated.metadata.ref
                conn.execute(
                    strategies.update()
                    .where(
                        strategies.c.strategy_id == ref.strategy_id,
                        strategies.c.version == ref.version,
                    )
                    .values(data=updated.model_dump_json())
                )
            conn.execute(
                strategies.update()
                .where(
                    strategies.c.strategy_id == serving.strategy_id,
                    strategies.c.version == serving.version,
                )
                .values(serving_id=serving.strategy_id)
            )
            conn.execute(
                evolutions.insert().values(
                    evolution_id=record.evolution_id,
                    strategy_id=expected_current.strategy_id,
                    data=record.model_dump_json(),
                )
            )
            conn.execute(
                evolution_claims.update()
                .where(evolution_claims.c.evolution_id == record.evolution_id)
                .values(active_strategy_id=None)
            )


class SQLiteExperienceStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def _save(self, key: str, kind: str, strategy: StrategyRef, scope: str, data: str) -> None:
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            previous = conn.execute(
                select(experiences.c.data).where(experiences.c.record_id == key)
            ).scalar()
            if previous is not None:
                if previous != data:
                    raise ValueError("经验 ID 已有不同内容，禁止覆盖")
                return
            conn.execute(
                experiences.insert().values(
                    record_id=key,
                    kind=kind,
                    strategy_id=strategy.strategy_id,
                    version=strategy.version,
                    scope=scope,
                    data=data,
                )
            )

    async def save_failure(self, experience: FailureExperience) -> None:
        self._save(
            experience.experience_id,
            "failure",
            experience.strategy,
            experience.task_scope,
            experience.model_dump_json(),
        )

    async def save_improvement(self, experience: ImprovementExperience) -> None:
        self._save(
            experience.experience_id,
            "improvement",
            experience.current,
            experience.task_scope,
            experience.model_dump_json(),
        )

    async def save_pattern(self, pattern: OutcomePattern) -> None:
        self._save(
            pattern.pattern_id,
            "pattern",
            pattern.strategy,
            pattern.task_scope,
            pattern.model_dump_json(),
        )

    async def list_patterns(
        self, strategy: StrategyRef, *, task_scope: str
    ) -> tuple[OutcomePattern, ...]:
        with self.engine.connect() as conn:
            values = (
                conn.execute(
                    select(experiences.c.data)
                    .where(
                        experiences.c.kind == "pattern",
                        experiences.c.strategy_id == strategy.strategy_id,
                        experiences.c.version == strategy.version,
                        experiences.c.scope == task_scope,
                    )
                    .order_by(experiences.c.record_id)
                )
                .scalars()
                .all()
            )
        return tuple(OutcomePattern.model_validate_json(value) for value in values)


class SQLiteMonitorStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    async def load(self, key: str) -> MonitorState:
        with self.engine.connect() as conn:
            data = conn.execute(
                select(monitor_states.c.data).where(monitor_states.c.key == key)
            ).scalar()
        return MonitorState.model_validate_json(data) if data else MonitorState()

    async def save(self, key: str, *, expected_revision: int, state: MonitorState) -> None:
        if state.revision != expected_revision + 1:
            raise ValueError("监控检查点必须递增 revision")
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            current = conn.execute(
                select(monitor_states.c.revision).where(monitor_states.c.key == key)
            ).scalar()
            if (current or 0) != expected_revision:
                raise ValueError("监控检查点发生并发变化，请重新观察")
            if current is None:
                conn.execute(
                    monitor_states.insert().values(
                        key=key, revision=state.revision, data=state.model_dump_json()
                    )
                )
            else:
                conn.execute(
                    monitor_states.update()
                    .where(monitor_states.c.key == key)
                    .values(revision=state.revision, data=state.model_dump_json())
                )


class SQLiteEvolutionStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    async def claim(
        self, evolution_id: str, strategy: StrategyRef, request_fingerprint: str
    ) -> EvolutionRecord | None:
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            claimed = conn.execute(
                select(evolution_claims).where(evolution_claims.c.evolution_id == evolution_id)
            ).one_or_none()
            if claimed is not None and claimed.request_fingerprint != request_fingerprint:
                raise ValueError("已消费 Trigger 的演进配置不能更改")
            completed = conn.execute(
                select(evolutions.c.data).where(evolutions.c.evolution_id == evolution_id)
            ).scalar()
            if completed is not None:
                return EvolutionRecord.model_validate_json(completed)
            active = conn.execute(
                select(evolution_claims.c.evolution_id).where(
                    evolution_claims.c.active_strategy_id == strategy.strategy_id
                )
            ).scalar()
            if claimed is not None or active is not None:
                raise ValueError("该 Strategy 的演进正在进行中，禁止重复启动")
            current_version = conn.execute(
                select(strategies.c.version).where(strategies.c.serving_id == strategy.strategy_id)
            ).scalar()
            if current_version != strategy.version:
                raise ValueError("Current 已变化，拒绝陈旧演进")
            conn.execute(
                evolution_claims.insert().values(
                    evolution_id=evolution_id,
                    request_fingerprint=request_fingerprint,
                    active_strategy_id=strategy.strategy_id,
                )
            )
        return None

    def _save_artifact(self, table: Table, key_column: Column, key: str, data: str) -> None:
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            previous = conn.execute(select(table.c.data).where(key_column == key)).scalar()
            if previous is not None:
                if previous != data:
                    raise ValueError("演进产物 ID 已有不同内容，禁止覆盖")
                return
            conn.execute(table.insert().values({key_column.name: key, "data": data}))

    async def save_attribution(self, report: AttributionReport) -> None:
        self._save_artifact(
            attributions,
            attributions.c.report_id,
            report.report_id,
            report.model_dump_json(),
        )

    async def get_attribution(self, report_id: str) -> AttributionReport:
        with self.engine.connect() as conn:
            data = conn.execute(
                select(attributions.c.data).where(attributions.c.report_id == report_id)
            ).scalar_one()
        return AttributionReport.model_validate_json(data)

    async def save_proposal(self, proposal: MutationProposal) -> None:
        self._save_artifact(
            mutation_proposals,
            mutation_proposals.c.proposal_id,
            proposal.proposal_id,
            proposal.model_dump_json(),
        )

    async def get_proposal(self, proposal_id: str) -> MutationProposal:
        with self.engine.connect() as conn:
            data = conn.execute(
                select(mutation_proposals.c.data).where(
                    mutation_proposals.c.proposal_id == proposal_id
                )
            ).scalar_one()
        return MutationProposal.model_validate_json(data)

    async def save_validation(self, result: ValidationResult) -> None:
        self._save_artifact(
            validations,
            validations.c.validation_id,
            result.validation_id,
            result.model_dump_json(),
        )

    async def get_validation(self, validation_id: str) -> ValidationResult:
        with self.engine.connect() as conn:
            data = conn.execute(
                select(validations.c.data).where(validations.c.validation_id == validation_id)
            ).scalar_one()
        return ValidationResult.model_validate_json(data)

    async def save_record(self, record: EvolutionRecord) -> None:
        data = record.model_dump_json()
        with self.engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            previous = conn.execute(
                select(evolutions.c.data).where(evolutions.c.evolution_id == record.evolution_id)
            ).scalar()
            if previous is not None:
                if previous != data:
                    raise ValueError("EvolutionRecord ID 已有不同内容，禁止覆盖")
                return
            conn.execute(
                evolutions.insert().values(
                    evolution_id=record.evolution_id,
                    strategy_id=record.trigger.strategy.strategy_id,
                    data=data,
                )
            )
            conn.execute(
                evolution_claims.update()
                .where(evolution_claims.c.evolution_id == record.evolution_id)
                .values(active_strategy_id=None)
            )

    async def get_record(self, evolution_id: str) -> EvolutionRecord:
        with self.engine.connect() as conn:
            data = conn.execute(
                select(evolutions.c.data).where(evolutions.c.evolution_id == evolution_id)
            ).scalar_one()
        return EvolutionRecord.model_validate_json(data)


class SQLiteStorage:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._engine: Engine | None = None

    def _connect(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self.database_url)
            if self._engine.dialect.name != "sqlite":
                self._engine.dispose()
                self._engine = None
                raise ValueError("仅支持 SQLite")
        return self._engine

    async def register_model(self, model: ModelEndpoint) -> None:
        """固定非敏感模型绑定；密钥仅用于当前进程，允许独立轮换。"""
        with self._connect().begin() as conn:
            conn.execute(
                model_configs.insert().values(
                    model_id=model.ref.id, version=model.ref.version, data=model.model_dump_json()
                )
            )

    async def require_model(self, model: ModelEndpoint) -> None:
        with self._connect().connect() as conn:
            data = conn.execute(
                select(model_configs.c.data).where(
                    model_configs.c.model_id == model.ref.id,
                    model_configs.c.version == model.ref.version,
                )
            ).scalar()
        if data is None or data != model.model_dump_json():
            raise ValueError("模型绑定与登记版本不一致；配置变更需要新版本")

    async def initialize(self) -> None:
        """显式创建当前所需表；后续 Schema 升级需迁移，不自动改现有表。"""
        metadata.create_all(self._connect())

    async def open(self) -> StoragePorts:
        engine = self._connect()
        if not set(metadata.tables) <= set(inspect(engine).get_table_names()):
            raise ValueError("数据库未初始化，请显式调用 initialize")
        return StoragePorts(
            SQLiteRunStore(engine),
            SQLiteStrategyStore(engine),
            SQLiteExperienceStore(engine),
            SQLiteEvolutionStore(engine),
            SQLiteMonitorStore(engine),
        )

    async def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
