"""Explicit field projections; connection settings and runtime context stay private."""

import re
from typing import Any

from evoteam.domain.agent import AgentResult
from evoteam.domain.events import EventType, TraceEvent
from evoteam.domain.planning import (
    ANALYSIS_SCHEMA,
    PLAN_SCHEMA,
    REVIEW_SCHEMA,
    PlanningAnalysis,
    PlanningInput,
    PlanningReview,
    ProjectPlan,
)
from evoteam.domain.run import SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.storage.protocol import RunStore


def redact(value: Any) -> Any:
    """Defense in depth for text embedded in otherwise whitelisted domain fields."""
    if isinstance(value, dict):
        return {
            k: redact(v)
            for k, v in value.items()
            if not re.search(
                r"api.?key|secret|password|authorization|base_url|endpoint|raw_log|context", k, re.I
            )
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)\b(?:bearer\s+|sk-)[\w.\-]+", "[已隐藏凭据]", value)
        value = re.sub(r"(?i)(?:api[_ -]?key|password|secret)\s*[:=]\s*\S+", "[已隐藏凭据]", value)
        value = re.sub(r'https?://[^\s"<>]+', "[已隐藏连接地址]", value)
        return re.sub(
            r'(?:[A-Za-z]:\\|/(?=Users/|home/|tmp/|private/|var/|etc/))[^\s"<>]+',
            "[已隐藏路径]",
            value,
        )
    return value


def public_output(result: AgentResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    schemas = {
        (PLAN_SCHEMA.id, PLAN_SCHEMA.version): ProjectPlan,
        (ANALYSIS_SCHEMA.id, ANALYSIS_SCHEMA.version): PlanningAnalysis,
        (REVIEW_SCHEMA.id, REVIEW_SCHEMA.version): PlanningReview,
    }
    schema = schemas.get((result.output_schema.id, result.output_schema.version))
    if schema is None:
        return None
    try:
        return schema.model_validate(result.output).model_dump(mode="json")
    except ValueError:
        return None


def summary(run: SealedRun) -> dict[str, Any]:
    return redact(
        run.model_dump(
            mode="json",
            include={
                "run_id",
                "task_id",
                "task_scope",
                "strategy",
                "purpose",
                "status",
                "sealed_at",
                "evaluation",
                "dataset_source",
            },
        )
    )


def strategy_view(strategy: Strategy) -> dict[str, Any]:
    return redact(strategy.model_dump(mode="json", include={"definition", "metadata"}))


NODE_STATE = {
    EventType.AGENT_STARTED: "running",
    EventType.AGENT_COMPLETED: "completed",
    EventType.AGENT_FAILED: "failed",
}


def event_view(event: TraceEvent) -> dict[str, Any]:
    """运行轨道用的白名单事件投影；payload、原始消息与 SDK 日志不外发。"""
    view = redact(
        event.model_dump(
            mode="json",
            include={
                "event_id",
                "event_type",
                "timestamp",
                "sequence",
                "run_id",
                "node_id",
                "instance_id",
                "caused_by",
            },
        )
    )
    view["node_state"] = NODE_STATE.get(event.event_type)
    view["output"] = None
    view["config"] = None
    if event.event_type is EventType.AGENT_COMPLETED:
        result = event.payload.get("result")
        if isinstance(result, dict):
            try:
                view["output"] = public_output(AgentResult.model_validate(result))
            except ValueError:
                pass
    elif event.event_type is EventType.TEAM_CREATED:
        plan = event.payload.get("plan")
        if isinstance(plan, dict):
            view["config"] = redact(
                {
                    "enabled_nodes": plan.get("enabled_node_ids"),
                    "edges": plan.get("edges"),
                }
            )
    return view


async def run_detail(store: RunStore, run_id: str) -> tuple[dict[str, Any], list[str]]:
    sealed = await store.get_sealed_run(run_id)
    result = dict(
        summary(sealed),
        task=None,
        plan=None,
        nodes=[],
        edges=[],
        instances=[],
        termination_reason=None,
    )
    missing: list[str] = []
    try:
        snapshot = await store.read_snapshot(run_id)
    except KeyError:
        return result, ["run_snapshot"]
    task, run = snapshot.task, snapshot.run
    result["task"] = {"task_id": task.task_id, "instruction": task.instruction, "inputs": None}
    try:
        result["task"]["inputs"] = PlanningInput.model_validate(task.inputs).model_dump(mode="json")
    except ValueError:
        missing.append("supported_task_input")
    plans = [item for item in run.results if item.output_schema == PLAN_SCHEMA]
    if plans:
        try:
            result["plan"] = ProjectPlan.model_validate(plans[-1].output).model_dump(mode="json")
        except ValueError:
            missing.append("valid_project_plan")
    else:
        missing.append("project_plan")
    result["termination_reason"] = run.termination_reason
    if run.team:
        enabled = run.team.execution_plan.enabled_node_ids
        result["nodes"] = [
            a.model_dump(mode="json")
            for a in snapshot.strategy.definition.agents
            if a.node_id in enabled
        ]
        result["edges"] = [e.model_dump(mode="json") for e in run.team.execution_plan.edges]
        result["instances"] = [
            {
                "instance_id": i.instance_id,
                "node_id": i.config.node_id,
                "state": i.state.value,
                "input_tokens": i.result.input_tokens if i.result else None,
                "output_tokens": i.result.output_tokens if i.result else None,
                "messages": [
                    m.model_dump(
                        mode="json",
                        include={
                            "message_id",
                            "sender_node_id",
                            "recipient_node_id",
                            "source_event_ids",
                        },
                    )
                    for m in i.messages
                ],
                "output": public_output(i.result),
            }
            for i in run.team.instances
        ]
        # Input payload and arbitrary runtime context are intentionally not exported.
    else:
        missing.append("execution_plan")
    return redact(result), missing
