"""模块装配根：只把依赖连接起来，不连接数据库、不执行 Task 或 LLM。"""

from dataclasses import dataclass

from evoteam.application import EvolutionService, TaskService
from evoteam.domain.events import TraceEvent
from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.datasets import PackagedValidationDatasets
from evoteam.evolution.gate import ValidationGate
from evoteam.evolution.lifecycle import StrategyLifecycle
from evoteam.evolution.manager import EvolutionManager
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import Validator
from evoteam.experience.aggregator import ExperienceAggregator
from evoteam.monitoring.strategy_monitor import StrategyMonitor
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.runtime.protocol import AgentRuntime
from evoteam.storage.protocol import RunStore
from evoteam.storage.sqlite import StoragePorts


@dataclass(frozen=True)
class StoreEventSink:
    """把 Runtime/Orchestrator 事件发送到统一 RunStore。"""

    runs: RunStore

    async def emit(self, event: TraceEvent) -> None:
        await self.runs.append_event(event)


@dataclass(frozen=True)
class EvoTeamApplication:
    """两个显式入口：在线执行、离线观察/演进。"""

    tasks: TaskService
    evolution: EvolutionService


def build_application(*, runtime: AgentRuntime, storage: StoragePorts) -> EvoTeamApplication:
    """把已经构造好的 Runtime 与 Repository 接入当前组件。

    已支持固定 v0、可选 Verifier DAG/返工、SQLite 封存与多候选离线演进。
    Tool Policy、更通用结构 Mutation 和其他监控信号仍未开放。
    """
    # 在线执行：一次 Task 的业务产物；Agent 调度只由这个 Orchestrator 管理。
    events = StoreEventSink(storage.runs)
    analyzer = TaskAnalyzer()
    orchestrator = Orchestrator(runtime, events)
    evaluator = ProjectPlanningEvaluator()
    tasks = TaskService(analyzer, orchestrator, evaluator, storage.runs, storage.strategies)

    # 验证复用同一执行器和评价器；不能另建一套更宽松的 Candidate 评分流程。
    validator = Validator(
        orchestrator,
        evaluator,
        analyzer,
        storage.runs,
        PackagedValidationDatasets(),
    )
    manager = EvolutionManager(
        attributor=OutcomeAttributor(),
        generator=CandidateGenerator(),
        validator=validator,
        gate=ValidationGate(),
        lifecycle=StrategyLifecycle(storage.strategies),
        strategies=storage.strategies,
        records=storage.evolutions,
    )
    # Store 只存数据、Aggregator 提炼经验、Monitor 看趋势、Manager 管离线流程。
    evolution = EvolutionService(
        storage.strategies,
        storage.runs,
        storage.experiences,
        ExperienceAggregator(),
        StrategyMonitor(),
        manager,
        monitor_store=storage.monitoring,
    )
    return EvoTeamApplication(tasks=tasks, evolution=evolution)
