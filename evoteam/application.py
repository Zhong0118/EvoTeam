"""模块级调度：在线任务与离线观察分开进入，不在每个任务中自动演进。"""

from dataclasses import dataclass
from uuid import uuid4

from evoteam.domain.evolution import EvolutionRecord, MonitorResult, ValidationPlan
from evoteam.domain.run import RunPurpose, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task
from evoteam.evaluation.evaluator import Evaluator
from evoteam.evolution.gate import GatePolicy
from evoteam.evolution.manager import EvolutionManager
from evoteam.experience.aggregator import ExperienceAggregator
from evoteam.experience.evidence import evidence_id
from evoteam.experience.store import ExperienceStore
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.monitoring.state import MonitorStore
from evoteam.monitoring.strategy_monitor import StrategyMonitor
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.storage.protocol import RunStore, StrategyStore

_TERMINAL = frozenset(
    {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.TIMED_OUT}
)


def _require_serving(strategy: Strategy, strategy_id: str) -> None:
    if strategy.metadata.ref.strategy_id != strategy_id:
        raise ValueError("Store 返回了其他 Strategy")
    if strategy.metadata.status not in (StrategyStatus.CURRENT, StrategyStatus.STABLE):
        raise ValueError("线上仅允许 CURRENT 或 STABLE Strategy")


class TaskService:
    """应用级执行顺序；Agent 内部调度仍由 Orchestrator 实现。"""

    def __init__(
        self,
        analyzer: TaskAnalyzer,
        orchestrator: Orchestrator,
        evaluator: Evaluator,
        runs: RunStore,
        strategies: StrategyStore,
    ) -> None:
        self.analyzer = analyzer
        self.orchestrator = orchestrator
        self.evaluator = evaluator
        self.runs = runs
        self.strategies = strategies

    async def execute(self, task: Task, *, strategy_id: str) -> SealedRun:
        """固定当前版本 → 解析 → 执行 → 独立评分 → Store 原子封存。

        Task 类型作为当前默认观察范围；细分范围尚未引入自动路由。
        失败/超时/取消 RunResult 同样评分封存。组件异常原样传播，不能返回假成功；
        Runtime 异常由 Orchestrator 转为终结 RunResult；基础设施故障恢复仍待实现。
        """
        task = task.model_copy(deep=True)
        strategy = await self.strategies.current(strategy_id)
        _require_serving(strategy, strategy_id)
        profile = self.analyzer.analyze(task)
        if profile.task_id != task.task_id or profile.task_type != task.task_type:
            raise ValueError("TaskProfile 与当前 Task 不匹配")

        run_id = str(uuid4())
        run = await self.orchestrator.execute(
            task,
            profile,
            strategy,
            run_id=run_id,
            purpose=RunPurpose.ONLINE,
        )
        if (
            run.run_id != run_id
            or run.task_id != task.task_id
            or run.strategy != strategy.metadata.ref
            or run.purpose != RunPurpose.ONLINE
        ):
            raise ValueError("RunResult 与当前 Task / Strategy / Run 不匹配")
        if run.status not in _TERMINAL:
            raise ValueError("Run 尚未结束，不能评价和封存")

        evaluation = await self.evaluator.evaluate(task, run)
        if evaluation.run_id != run_id:
            raise ValueError("EvaluationResult 与当前 Run 不匹配")
        # Store 必须保存真实快照和评价后返回索引；应用层不伪造 snapshot_ref。
        sealed = await self.runs.seal_run(task, run, evaluation, task_scope=task.task_type.value)
        if (
            sealed.run_id != run_id
            or sealed.task_id != task.task_id
            or sealed.strategy != run.strategy
            or sealed.purpose != run.purpose
            or sealed.status != run.status
            or sealed.evaluation != evaluation
            or sealed.task_scope != task.task_type.value
        ):
            raise ValueError("封存记录与已执行的 Run 不匹配")
        return sealed


@dataclass(frozen=True)
class Observation:
    """把同一次观察的版本、证据和判断一起传递，避免二次查询换了样本。"""

    strategy: Strategy
    runs: tuple[SealedRun, ...]
    result: MonitorResult


class EvolutionService:
    """显式观察/离线入口；只有 Monitor 给出 Trigger 才调用演进总控。"""

    def __init__(
        self,
        strategies: StrategyStore,
        runs: RunStore,
        experiences: ExperienceStore,
        aggregator: ExperienceAggregator,
        monitor: StrategyMonitor,
        manager: EvolutionManager,
        monitor_store: MonitorStore | None = None,
    ) -> None:
        self.strategies = strategies
        self.runs = runs
        self.experiences = experiences
        self.aggregator = aggregator
        self.monitor = monitor
        self.manager = manager
        self.monitor_store = monitor_store

    async def inspect(
        self, *, strategy_id: str, task_scope: str, policy: EvolutionPolicy
    ) -> Observation:
        """读取线上证据 → 校验窗口 → 聚合并存经验 → Monitor；不启动演进。"""
        strategy = await self.strategies.current(strategy_id)
        _require_serving(strategy, strategy_id)
        runs = await self.runs.recent_runs(
            strategy.metadata.ref,
            task_scope=task_scope,
            purpose=RunPurpose.ONLINE,
            limit=policy.window_size,
        )
        run_ids = {run.run_id for run in runs}
        if len(run_ids) != len(runs) or len(runs) > policy.window_size:
            raise ValueError("观察窗口含重复 Run 或超过 window_size")
        for run in runs:
            if (
                run.purpose != RunPurpose.ONLINE
                or run.strategy != strategy.metadata.ref
                or run.task_scope != task_scope
            ):
                raise ValueError("观察窗口只能包含同策略、同范围的 online 线上 Run")
            if run.status not in _TERMINAL or run.evaluation.run_id != run.run_id:
                raise ValueError("观察窗口包含未终结或评价身份不匹配的 Run")
        if (
            len(
                {
                    (run.evaluation.evaluator_ref.id, run.evaluation.evaluator_ref.version)
                    for run in runs
                }
            )
            > 1
        ):
            raise ValueError("观察窗口混合了不同版本的 Evaluator")

        patterns = self.aggregator.aggregate(runs)
        # 先检查全部输出，再持久化，避免部分污染。
        for pattern in patterns:
            if (
                pattern.strategy != strategy.metadata.ref
                or pattern.task_scope != task_scope
                or not set(pattern.supporting_runs).issubset(run_ids)
            ):
                raise ValueError("经验模式与观察证据不匹配")
        for pattern in patterns:
            await self.experiences.save_pattern(pattern)

        checkpoint = None
        next_checkpoint = None
        checkpoint_key = evidence_id(
            "monitor",
            [
                strategy.metadata.ref.model_dump(),
                task_scope,
                policy.ref.model_dump(),
                runs[0].evaluation.evaluator_ref.model_dump() if runs else None,
            ],
        )
        if self.monitor_store is None:
            result = self.monitor.inspect(strategy, runs, policy)
        else:
            checkpoint = await self.monitor_store.load(checkpoint_key)
            result, next_checkpoint = self.monitor.observe(strategy, runs, policy, checkpoint)
        if result.strategy != strategy.metadata.ref or result.sample_count != len(runs):
            raise ValueError("MonitorResult 与观察窗口不匹配")
        trigger = result.trigger
        if trigger is not None:
            if (
                trigger.strategy != strategy.metadata.ref
                or trigger.policy_ref != policy.ref
                or trigger.task_scope != task_scope
                or not trigger.evidence_run_ids
                or len(set(trigger.evidence_run_ids)) != len(trigger.evidence_run_ids)
                or not set(trigger.evidence_run_ids).issubset(run_ids)
                or len(runs) < policy.min_samples
            ):
                raise ValueError("Trigger 与策略、Policy 或证据窗口不匹配")
        if (
            self.monitor_store is not None
            and checkpoint is not None
            and next_checkpoint is not None
            and next_checkpoint.revision != checkpoint.revision
        ):
            await self.monitor_store.save(
                checkpoint_key, expected_revision=checkpoint.revision, state=next_checkpoint
            )
        return Observation(strategy=strategy, runs=runs, result=result)

    async def evolve_if_needed(
        self,
        *,
        strategy_id: str,
        task_scope: str,
        policy: EvolutionPolicy,
        validation_plan: ValidationPlan,
        gate_policy: GatePolicy,
    ) -> EvolutionRecord | None:
        """显式离线入口；None 表示本次无 Trigger，不生成候选。

        此处只负责派发。Manager 仍负责完整离线流程、Trigger 去重和审计；
        Lifecycle/Store 最终用 expected_current 事务检查解决并发版本竞争。
        """
        observation = await self.inspect(
            strategy_id=strategy_id, task_scope=task_scope, policy=policy
        )
        trigger = observation.result.trigger
        if trigger is None:
            return None
        latest = await self.strategies.current(strategy_id)
        _require_serving(latest, strategy_id)
        if latest != observation.strategy:
            raise ValueError("观察期间 Current 已变更，需重新观察，不能派发陈旧 Trigger")
        return await self.manager.evolve(
            trigger,
            observation.strategy,
            observation.runs,
            policy,
            validation_plan,
            gate_policy,
        )
