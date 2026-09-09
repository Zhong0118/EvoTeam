"""固定 v0 顺序执行；框架调用在 Runtime，策略治理不进入在线路径。"""

import asyncio
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from pydantic import JsonValue

from evoteam.capabilities.prompts import load_prompt
from evoteam.domain.agent import AgentInstance, AgentMessage, AgentState
from evoteam.domain.events import EventType, TraceEvent
from evoteam.domain.planning import (
    AGENT_INPUT_SCHEMA,
    ANALYSIS_SCHEMA,
    PLAN_SCHEMA,
    REVIEW_SCHEMA,
    PlanningAgentInput,
    PlanningAnalysis,
    PlanningReview,
    ProjectPlan,
    parse_planning_task,
)
from evoteam.domain.role import RoleType
from evoteam.domain.run import ExecutionPlan, RunPurpose, RunResult, RunStatus, Team
from evoteam.domain.strategy import ExecutionMode, Strategy, StrategyStatus
from evoteam.domain.task import Task, TaskProfile
from evoteam.runtime.protocol import AgentRuntime, EventSink, RuntimeAgent, RuntimeContext


def validate_v0(strategy: Strategy, purpose: RunPurpose) -> None:
    """当前执行器只接受已实现的三节点链；不支持的能力显式拒绝。"""
    definition = strategy.definition
    agents = definition.agents
    policy = definition.orchestration
    allowed = {StrategyStatus.CURRENT, StrategyStatus.STABLE}
    if purpose == RunPurpose.VALIDATION:
        allowed |= {StrategyStatus.CANDIDATE, StrategyStatus.VALIDATING}
    if strategy.metadata.status not in allowed:
        raise ValueError("策略状态不能用于当前运行用途")
    if tuple(a.role for a in agents) != (RoleType.PLANNER, RoleType.EXECUTOR, RoleType.CRITIC):
        raise ValueError("当前仅支持 Planner → Executor → Critic")
    ids = tuple(a.node_id for a in agents)
    expected = {(ids[0], ids[1]), (ids[1], ids[2])}
    if (
        len(set(ids)) != 3
        or len(definition.edges) != 2
        or {(e.source, e.target) for e in definition.edges} != expected
        or any(e.condition_ref for e in definition.edges)
    ):
        raise ValueError("不支持的拓扑或节点引用")
    if policy.mode != ExecutionMode.SEQUENTIAL or policy.retry_limit or policy.replan_limit:
        raise ValueError("当前只支持顺序执行且不开启 Retry / Replan")
    if (
        policy.budget.max_tokens is None
        or policy.budget.timeout_seconds is None
        or policy.budget.max_tool_calls != 0
    ):
        raise ValueError("必须配置 Token、超时；当前 Tool 上限必须为 0")
    for config in agents:
        load_prompt(config.prompt_ref)
        if (
            config.skill_refs
            or config.tool_policy.allowed_tools
            or config.tool_policy.required_tools
            or config.runtime_config.max_retries
        ):
            raise ValueError("当前执行路径尚不支持 Skill、Tool 或重试")
        if config.runtime_config.timeout_seconds is None:
            raise ValueError("必须配置每个 Agent 的超时")


class Orchestrator:
    def __init__(self, runtime: AgentRuntime, events: EventSink) -> None:
        self.runtime = runtime
        self.events = events

    async def execute(
        self,
        task: Task,
        profile: TaskProfile,
        strategy: Strategy,
        *,
        run_id: str,
        purpose: RunPurpose,
    ) -> RunResult:
        parse_planning_task(task)
        if profile.task_id != task.task_id or profile.task_type != task.task_type:
            raise ValueError("画像与 Task 不匹配")
        validate_v0(strategy, purpose)
        # 运行快照与调用者的可变 Task/Profile 隔离。
        task = task.model_copy(deep=True)
        definition = strategy.definition
        budget = definition.orchestration.budget
        assert budget.max_tokens is not None and budget.timeout_seconds is not None
        team = Team(
            team_id=str(uuid4()),
            strategy=strategy.metadata.ref,
            execution_plan=ExecutionPlan(
                enabled_node_ids=tuple(a.node_id for a in definition.agents), edges=definition.edges
            ),
        )
        run = RunResult(
            run_id=run_id,
            task_id=task.task_id,
            strategy=strategy.metadata.ref,
            purpose=purpose,
            status=RunStatus.RUNNING,
            team=team,
        )
        started_at = monotonic()
        run.tool_calls = 0
        run.retry_count = 0
        trace: list[str] = []
        active: AgentInstance | None = None
        handles: list[tuple[RuntimeAgent, float]] = []

        async def emit(kind: EventType, payload: dict[str, JsonValue] | None = None) -> None:
            event = TraceEvent(
                event_id=str(uuid4()),
                event_type=kind,
                timestamp=datetime.now(UTC),
                sequence=len(trace),
                strategy=strategy.metadata.ref,
                run_id=run_id,
                task_id=task.task_id,
                node_id=active.config.node_id if active else None,
                instance_id=active.instance_id if active else None,
                caused_by=(trace[-1],) if trace else (),
                payload=payload or {},
            )
            await self.events.emit(event)
            trace.append(event.event_id)

        await emit(EventType.TASK_CREATED, {"task": task.model_dump(mode="json")})
        await emit(EventType.TEAM_CREATED, {"plan": team.execution_plan.model_dump(mode="json")})
        schemas = (
            (ANALYSIS_SCHEMA, PlanningAnalysis),
            (PLAN_SCHEMA, ProjectPlan),
            (REVIEW_SCHEMA, PlanningReview),
        )
        remaining = budget.max_tokens
        upstream: dict[str, JsonValue] = {}
        upstream_event_id = trace[0]
        sender = None
        rejected_result: dict[str, JsonValue] | None = None
        try:
            async with asyncio.timeout(budget.timeout_seconds):
                for config, (schema, output_model) in zip(definition.agents, schemas, strict=True):
                    if remaining <= 0:
                        raise ValueError("Token 预算耗尽")
                    timeout = config.runtime_config.timeout_seconds
                    assert timeout is not None
                    active = AgentInstance(
                        instance_id=str(uuid4()), run_id=run_id, task_id=task.task_id, config=config
                    )
                    team.instances.append(active)
                    async with asyncio.timeout(timeout):
                        handle = await self.runtime.create_agent(config, run_id=run_id)
                        handles.append((handle, timeout))
                        if handle.run_id != run_id or handle.node_id != config.node_id:
                            raise ValueError("Runtime 句柄身份不匹配")
                        active.instance_id = handle.handle_id
                        active.state = AgentState.RUNNING
                        await emit(EventType.AGENT_STARTED)
                        message = AgentMessage(
                            message_id=str(uuid4()),
                            sender_node_id=sender,
                            recipient_node_id=config.node_id,
                            schema_ref=AGENT_INPUT_SCHEMA,
                            payload=PlanningAgentInput(task=task, upstream=upstream).model_dump(
                                mode="json"
                            ),
                            source_event_ids=(upstream_event_id,),
                        )
                        active.messages.append(message.model_copy(deep=True))
                        await emit(
                            EventType.AGENT_MESSAGE, {"message": message.model_dump(mode="json")}
                        )
                        result = await self.runtime.invoke(
                            handle,
                            message,
                            RuntimeContext(
                                run_id=run_id,
                                task_id=task.task_id,
                                source_event_ids=(trace[-1],),
                                budget=budget.model_copy(update={"max_tokens": remaining}),
                            ),
                        )
                        if (
                            result.instance_id != active.instance_id
                            or result.output_schema != schema
                        ):
                            rejected_result = result.model_dump(mode="json")
                            raise ValueError("Agent 输出身份或 Schema 不匹配")
                        # 保留包括非法产物在内的返回证据，便于独立评分和故障定位。
                        active.result = result.model_copy(deep=True)
                        run.results.append(active.result)
                        output_model.model_validate(result.output)
                        if result.tool_result_refs:
                            raise ValueError("当前无 Tool 授权")
                        if result.input_tokens is None or result.output_tokens is None:
                            raise ValueError("缺少 Token 用量，无法执行预算控制")
                        remaining -= result.input_tokens + result.output_tokens
                        if remaining < 0:
                            raise ValueError("Runtime 返回用量超过剩余 Token 预算")
                        active.state = AgentState.COMPLETED
                        await emit(
                            EventType.AGENT_COMPLETED,
                            {"result": active.result.model_dump(mode="json")},
                        )
                        upstream = active.result.model_dump(mode="json")["output"]
                        upstream_event_id = trace[-1]
                        sender = config.node_id
                        active = None
            run.status = RunStatus.COMPLETED
        except asyncio.CancelledError:
            run.status = RunStatus.CANCELLED
            run.termination_reason = "调用者取消"
        except TimeoutError:
            run.status = RunStatus.TIMED_OUT
            run.termination_reason = "运行或 Agent 超时"
        except Exception as exc:
            run.status = RunStatus.FAILED
            # 不把 SDK 异常正文（可能含凭据）写入通用 Trace。
            run.termination_reason = type(exc).__name__
        finally:

            async def release_handles() -> bool:
                failed = False
                for handle, timeout in reversed(handles):
                    try:
                        async with asyncio.timeout(timeout):
                            await self.runtime.close(handle)
                    except (Exception, asyncio.CancelledError):
                        failed = True
                return failed

            # 调用者取消不传递给清理子任务；每个 close 仍受已配置的超时约束。
            cleanup = asyncio.create_task(release_handles())
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    run.status = RunStatus.CANCELLED
                    run.termination_reason = "调用者取消"
            if cleanup.result():
                if run.status != RunStatus.CANCELLED:
                    run.status = RunStatus.FAILED
                run.termination_reason = "Runtime 资源释放失败"
        if active and run.status != RunStatus.COMPLETED:
            active.state = AgentState(run.status.value)
            failure: dict[str, JsonValue] = {"reason": run.termination_reason}
            if rejected_result is not None:
                failure["rejected_result"] = rejected_result
            await emit(EventType.AGENT_FAILED, failure)
        active = None
        await emit(
            EventType.RUN_FINISHED, {"status": run.status.value, "reason": run.termination_reason}
        )
        run.latency_seconds = monotonic() - started_at
        run.trace_refs = tuple(trace)
        return run
