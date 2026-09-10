"""受限项目规划 DAG 执行器；支持可选 Verifier 与一次有界返工。"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from graphlib import CycleError, TopologicalSorter
from time import monotonic
from uuid import uuid4

from pydantic import JsonValue

from evoteam.capabilities.prompts import load_prompt
from evoteam.domain.agent import AgentConfig, AgentInstance, AgentMessage, AgentState
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

_SCHEMAS = {
    RoleType.PLANNER: (ANALYSIS_SCHEMA, PlanningAnalysis),
    RoleType.EXECUTOR: (PLAN_SCHEMA, ProjectPlan),
    RoleType.VERIFIER: (REVIEW_SCHEMA, PlanningReview),
    RoleType.CRITIC: (REVIEW_SCHEMA, PlanningReview),
}


def validate_strategy(strategy: Strategy, purpose: RunPurpose) -> tuple[AgentConfig, ...]:
    """只接受三节点链或带一个 Verifier 的已登记无环图。"""
    definition = strategy.definition
    agents = definition.agents
    policy = definition.orchestration
    allowed = {StrategyStatus.CURRENT, StrategyStatus.STABLE}
    if purpose == RunPurpose.VALIDATION:
        allowed |= {StrategyStatus.CANDIDATE, StrategyStatus.VALIDATING}
    if strategy.metadata.status not in allowed:
        raise ValueError("策略状态不能用于当前运行用途")
    ids = tuple(a.node_id for a in agents)
    if len(set(ids)) != len(ids):
        raise ValueError("Strategy 节点 ID 必须唯一")
    by_role: dict[RoleType, list[AgentConfig]] = defaultdict(list)
    for agent in agents:
        by_role[agent.role].append(agent)
    if any(
        len(by_role[role]) != 1 for role in (RoleType.PLANNER, RoleType.EXECUTOR, RoleType.CRITIC)
    ):
        raise ValueError("项目规划 Strategy 必须各有一个 Planner、Executor、Critic")
    if len(by_role[RoleType.VERIFIER]) > 1 or set(by_role) - set(_SCHEMAS):
        raise ValueError("当前只支持至多一个 Verifier，不支持其他 Role")
    if len(agents) not in {3, 4}:
        raise ValueError("当前项目规划 DAG 只支持 3 或 4 个节点")
    edge_pairs = tuple((edge.source, edge.target) for edge in definition.edges)
    if len(set(edge_pairs)) != len(edge_pairs) or any(
        edge.condition_ref for edge in definition.edges
    ):
        raise ValueError("边必须唯一，且当前不支持条件表达式")
    if any(
        source not in ids or target not in ids or source == target for source, target in edge_pairs
    ):
        raise ValueError("Strategy 含悬空边或自环")
    planner = by_role[RoleType.PLANNER][0].node_id
    executor = by_role[RoleType.EXECUTOR][0].node_id
    critic = by_role[RoleType.CRITIC][0].node_id
    expected = {(planner, executor), (executor, critic)}
    if by_role[RoleType.VERIFIER]:
        verifier = by_role[RoleType.VERIFIER][0].node_id
        expected |= {(executor, verifier), (verifier, critic)}
    if set(edge_pairs) != expected:
        raise ValueError("当前 DAG 只开放 Planner→Executor→Critic 及可选 Verifier 复核分支")
    graph = {node_id: set() for node_id in ids}
    for source, target in edge_pairs:
        graph[target].add(source)
    try:
        ordered_ids = tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise ValueError("Strategy DAG 不能包含循环") from exc
    if policy.mode != ExecutionMode.SEQUENTIAL or policy.retry_limit > 1 or policy.replan_limit:
        raise ValueError("当前只支持顺序 DAG、最多一次返工且不开启 Replan")
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
    by_id = {agent.node_id: agent for agent in agents}
    return tuple(by_id[node_id] for node_id in ordered_ids)


def validate_v0(strategy: Strategy, purpose: RunPurpose) -> None:
    """兼容旧入口；现在委托给受限 DAG 校验器。"""
    validate_strategy(strategy, purpose)


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
        order = validate_strategy(strategy, purpose)
        task = task.model_copy(deep=True)
        definition = strategy.definition
        budget = definition.orchestration.budget
        assert budget.max_tokens is not None and budget.timeout_seconds is not None
        team = Team(
            team_id=str(uuid4()),
            strategy=strategy.metadata.ref,
            execution_plan=ExecutionPlan(
                enabled_node_ids=tuple(config.node_id for config in order), edges=definition.edges
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
        rejected_result: dict[str, JsonValue] | None = None
        handles: list[tuple[RuntimeAgent, float]] = []
        outputs: dict[str, dict[str, JsonValue]] = {}
        completion_events: dict[str, str] = {}
        predecessors: dict[str, list[str]] = defaultdict(list)
        for edge in definition.edges:
            predecessors[edge.target].append(edge.source)
        by_role = {config.role: config for config in order}

        async def emit(
            kind: EventType,
            payload: dict[str, JsonValue] | None = None,
            *,
            causes: tuple[str, ...] | None = None,
        ) -> None:
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
                caused_by=causes if causes is not None else ((trace[-1],) if trace else ()),
                payload=payload or {},
            )
            await self.events.emit(event)
            trace.append(event.event_id)

        remaining = budget.max_tokens

        def upstream_for(node_id: str) -> tuple[dict[str, JsonValue], tuple[str, ...], str | None]:
            parents = predecessors[node_id]
            if not parents:
                return {}, (trace[0],), None
            source_events = tuple(completion_events[parent] for parent in parents)
            if len(parents) == 1:
                return outputs[parents[0]], source_events, parents[0]
            return {parent: outputs[parent] for parent in parents}, source_events, None

        async def invoke_node(
            config: AgentConfig,
            upstream: dict[str, JsonValue],
            source_events: tuple[str, ...],
            sender: str | None,
        ) -> None:
            nonlocal active, rejected_result, remaining
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
                await emit(EventType.AGENT_STARTED, causes=source_events)
                message = AgentMessage(
                    message_id=str(uuid4()),
                    sender_node_id=sender,
                    recipient_node_id=config.node_id,
                    schema_ref=AGENT_INPUT_SCHEMA,
                    payload=PlanningAgentInput(task=task, upstream=upstream).model_dump(
                        mode="json"
                    ),
                    source_event_ids=source_events,
                )
                active.messages.append(message.model_copy(deep=True))
                await emit(EventType.AGENT_MESSAGE, {"message": message.model_dump(mode="json")})
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
                schema_ref, output_model = _SCHEMAS[config.role]
                if result.instance_id != active.instance_id or result.output_schema != schema_ref:
                    rejected_result = result.model_dump(mode="json")
                    raise ValueError("Agent 输出身份或 Schema 不匹配")
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
                    EventType.AGENT_COMPLETED, {"result": active.result.model_dump(mode="json")}
                )
                outputs[config.node_id] = active.result.model_dump(mode="json")["output"]
                completion_events[config.node_id] = trace[-1]
                active = None

        await emit(EventType.TASK_CREATED, {"task": task.model_dump(mode="json")})
        await emit(EventType.TEAM_CREATED, {"plan": team.execution_plan.model_dump(mode="json")})
        try:
            async with asyncio.timeout(budget.timeout_seconds):
                for config in order:
                    upstream, sources, sender = upstream_for(config.node_id)
                    await invoke_node(config, upstream, sources, sender)
                critic = by_role[RoleType.CRITIC]
                verdict = PlanningReview.model_validate(outputs[critic.node_id])
                if not verdict.passed and definition.orchestration.retry_limit == 1:
                    run.retry_count = 1
                    executor = by_role[RoleType.EXECUTOR]
                    planner = by_role[RoleType.PLANNER]
                    await invoke_node(
                        executor,
                        {
                            "planner": outputs[planner.node_id],
                            "critic_feedback": outputs[critic.node_id],
                        },
                        (completion_events[planner.node_id], completion_events[critic.node_id]),
                        None,
                    )
                    verifier = by_role.get(RoleType.VERIFIER)
                    if verifier is not None:
                        await invoke_node(
                            verifier,
                            outputs[executor.node_id],
                            (completion_events[executor.node_id],),
                            executor.node_id,
                        )
                        critic_input: dict[str, JsonValue] = {
                            executor.node_id: outputs[executor.node_id],
                            verifier.node_id: outputs[verifier.node_id],
                        }
                        critic_sources = (
                            completion_events[executor.node_id],
                            completion_events[verifier.node_id],
                        )
                        critic_sender = None
                    else:
                        critic_input = outputs[executor.node_id]
                        critic_sources = (completion_events[executor.node_id],)
                        critic_sender = executor.node_id
                    await invoke_node(critic, critic_input, critic_sources, critic_sender)
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
