"""真实控制器、评价器和 SQLite；仅模型调用由脚本替身提供。"""

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import JsonValue

from evoteam.bootstrap import build_v0_strategy
from evoteam.composition import build_application
from evoteam.domain.agent import AgentResult
from evoteam.domain.common import AssetRef
from evoteam.domain.events import EventType
from evoteam.domain.run import RunPurpose, RunStatus
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task
from evoteam.storage.sqlite import SQLiteStorage

EXAMPLE = Path(__file__).parents[1] / "examples" / "project_planning"


def configured_strategy():
    data = build_v0_strategy(model_ref=AssetRef(id="fake", version="1")).model_dump()
    data["metadata"]["status"] = "current"
    data["definition"]["orchestration"]["budget"] = {
        "max_tokens": 100,
        "max_tool_calls": 0,
        "timeout_seconds": 2,
    }
    for agent in data["definition"]["agents"]:
        agent["runtime_config"]["timeout_seconds"] = 0.2
    return Strategy.model_validate(data)


class ScriptedRuntime:
    def __init__(self, failure=None):
        self.failure = failure
        self.closed = []
        self.messages = []

    async def create_agent(self, config, *, run_id):
        from evoteam.runtime.protocol import RuntimeAgent

        return RuntimeAgent(
            handle_id=f"{run_id}:{config.node_id}", run_id=run_id, node_id=config.node_id
        )

    async def invoke(self, agent, message, context):
        self.messages.append(message)
        if agent.node_id == "executor":
            if self.failure == "exception":
                raise RuntimeError("injected")
            if self.failure == "timeout":
                await asyncio.sleep(5)
            if self.failure == "cancel":
                raise asyncio.CancelledError()
        values = {
            "planner": ("planning-analysis", {"summary": "按依赖执行", "constraint_refs": []}),
            "executor": ("project-plan", json.loads((EXAMPLE / "plan.json").read_text())),
            "critic": ("planning-review", {"passed": True, "issues": []}),
        }
        schema, output = values[agent.node_id]
        if self.failure == "malformed" and agent.node_id == "executor":
            output = dict[str, JsonValue](wrong=True)
        if self.failure == "overbudget" and agent.node_id == "executor":
            tokens = 101
        else:
            tokens = 1
        return AgentResult(
            instance_id=agent.handle_id,
            output_schema=AssetRef(id=schema, version="1"),
            output=output,
            input_tokens=tokens,
            output_tokens=1,
        )

    async def close(self, agent):
        self.closed.append(agent.node_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,status",
    [
        (None, RunStatus.COMPLETED),
        ("exception", RunStatus.FAILED),
        ("timeout", RunStatus.TIMED_OUT),
        ("cancel", RunStatus.CANCELLED),
        ("malformed", RunStatus.FAILED),
        ("overbudget", RunStatus.FAILED),
    ],
)
async def test_online_run_survives_reopen_with_trace_and_failure_evidence(
    tmp_path, failure, status
):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    await storage.initialize()
    ports = await storage.open()
    strategy = configured_strategy()
    await ports.strategies.save(strategy)
    runtime = ScriptedRuntime(failure)
    task = Task.model_validate_json((EXAMPLE / "task.json").read_text())
    app = build_application(runtime=runtime, storage=ports)
    sealed = await app.tasks.execute(task, strategy_id="project-planning")
    assert sealed.status == status
    assert sealed.evaluation.metrics.success == (status == RunStatus.COMPLETED)
    assert set(runtime.closed) == (
        {"planner", "executor", "critic"} if failure is None else {"planner", "executor"}
    )
    if failure is None:
        assert runtime.messages[1].schema_ref == AssetRef(id="planning-agent-input", version="1")
        assert runtime.messages[1].sender_node_id == "planner"
        assert runtime.messages[2].sender_node_id == "executor"
        assert runtime.messages[2].payload["upstream"]["schedule"][1]["end_hour"] == 6
    await storage.close()

    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    ports = await storage.open()
    history = await ports.runs.recent_runs(
        strategy.metadata.ref, task_scope="project_planning", purpose=RunPurpose.ONLINE, limit=10
    )
    assert history == (sealed,)
    snapshot = await ports.runs.read_snapshot(sealed.run_id)
    assert snapshot.strategy == strategy
    assert snapshot.task == task
    assert snapshot.run.status == status
    events = await ports.runs.events_for_run(sealed.run_id)
    if failure is None:
        by_id = {event.event_id: event for event in events}
        for message in runtime.messages[1:]:
            source = by_id[message.source_event_ids[0]]
            assert source.event_type == EventType.AGENT_COMPLETED
            assert source.node_id == message.sender_node_id
    assert events[-2].event_type == EventType.EVALUATION_COMPLETED
    assert events[-1].event_type == EventType.RUN_SEALED
    assert any(event.event_type == EventType.RUN_FINISHED for event in events)
    assert tuple(event.event_id for event in events) == sealed.trace_refs
    with pytest.raises(ValueError):
        await ports.runs.seal_run(
            task, snapshot.run, sealed.evaluation, task_scope="project_planning"
        )
    assert (
        await ports.runs.recent_runs(
            strategy.metadata.ref,
            task_scope="project_planning",
            purpose=RunPurpose.VALIDATION,
            limit=10,
        )
        == ()
    )
    snapshot.task.instruction = "changed after reading"
    assert (await ports.runs.read_snapshot(sealed.run_id)).task.instruction == task.instruction
    await storage.close()


@pytest.mark.asyncio
async def test_unsupported_strategy_is_rejected_before_runtime(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'runs.db'}")
    await storage.initialize()
    ports = await storage.open()
    data = configured_strategy().model_dump()
    data["definition"]["edges"] = []
    await ports.strategies.save(Strategy.model_validate(data))
    runtime = ScriptedRuntime()
    app = build_application(runtime=runtime, storage=ports)
    with pytest.raises(ValueError):
        await app.tasks.execute(
            Task.model_validate_json((EXAMPLE / "task.json").read_text()),
            strategy_id="project-planning",
        )
    assert runtime.messages == []
    await storage.close()


@pytest.mark.asyncio
async def test_seal_transaction_rolls_back_events_when_snapshot_insert_fails(tmp_path):
    from sqlalchemy import create_engine

    from evoteam.composition import StoreEventSink
    from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
    from evoteam.orchestration.orchestrator import Orchestrator
    from evoteam.orchestration.task_analyzer import TaskAnalyzer

    url = f"sqlite:///{tmp_path / 'runs.db'}"
    storage = SQLiteStorage(url)
    await storage.initialize()
    ports = await storage.open()
    strategy = configured_strategy()
    await ports.strategies.save(strategy)
    task = Task.model_validate_json((EXAMPLE / "task.json").read_text())
    run = await Orchestrator(ScriptedRuntime(), StoreEventSink(ports.runs)).execute(
        task,
        TaskAnalyzer().analyze(task),
        strategy,
        run_id="rollback-test",
        purpose=RunPurpose.ONLINE,
    )
    evaluation = await ProjectPlanningEvaluator().evaluate(task, run)
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TRIGGER reject_snapshot BEFORE INSERT ON runs "
            "BEGIN SELECT RAISE(ABORT, 'injected disk write failure'); END"
        )
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await ports.runs.seal_run(task, run, evaluation, task_scope="project_planning")
    assert tuple(e.event_id for e in await ports.runs.events_for_run(run.run_id)) == run.trace_refs
    assert (
        await ports.runs.recent_runs(
            strategy.metadata.ref, task_scope="project_planning", purpose=RunPurpose.ONLINE, limit=1
        )
        == ()
    )
    engine.dispose()
    await storage.close()


def test_demo_cli_runs_without_credentials_and_does_not_overwrite_database(tmp_path):
    import subprocess
    import sys

    database = tmp_path / "demo.db"
    command = [sys.executable, "-m", "evoteam", "demo", "--database", str(database)]
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "completed"
    assert result["evaluation"]["metrics"]["success"] is True
    assert result["evaluation"]["metrics"]["quality"] is None
    before = database.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
    assert database.read_bytes() == before


@pytest.mark.asyncio
async def test_task_snapshot_is_fixed_before_runtime_await(tmp_path):
    original = Task.model_validate_json((EXAMPLE / "task.json").read_text())

    class MutatingRuntime(ScriptedRuntime):
        async def invoke(self, agent, message, context):
            original.inputs["budget_minor"] = 0
            return await super().invoke(agent, message, context)

    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'snapshot.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_strategy())
    sealed = await build_application(runtime=MutatingRuntime(), storage=ports).tasks.execute(
        original, strategy_id="project-planning"
    )
    assert sealed.evaluation.metrics.success is True
    assert (await ports.runs.read_snapshot(sealed.run_id)).task.inputs["budget_minor"] == 800
    await storage.close()


@pytest.mark.asyncio
async def test_exact_token_exhaustion_does_not_blame_completed_agent(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'budget.db'}")
    await storage.initialize()
    ports = await storage.open()
    data = configured_strategy().model_dump()
    data["definition"]["orchestration"]["budget"]["max_tokens"] = 2
    await ports.strategies.save(Strategy.model_validate(data))
    result = await build_application(runtime=ScriptedRuntime(), storage=ports).tasks.execute(
        Task.model_validate_json((EXAMPLE / "task.json").read_text()),
        strategy_id="project-planning",
    )
    assert result.status == RunStatus.FAILED
    snapshot = await ports.runs.read_snapshot(result.run_id)
    assert snapshot.run.team is not None
    assert snapshot.run.team.instances[0].state.value == "completed"
    assert not any(
        event.event_type == EventType.AGENT_FAILED
        for event in await ports.runs.events_for_run(result.run_id)
    )
    await storage.close()


@pytest.mark.asyncio
async def test_external_cancel_during_cleanup_finishes_cleanup_and_archives_cancellation(tmp_path):
    cleanup_started = asyncio.Event()
    allow_cleanup = asyncio.Event()

    class WaitingRuntime(ScriptedRuntime):
        async def close(self, agent):
            if agent.node_id == "critic":
                cleanup_started.set()
                await allow_cleanup.wait()
            await super().close(agent)

    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'cancel.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_strategy())
    runtime = WaitingRuntime()
    service = build_application(runtime=runtime, storage=ports).tasks
    worker = asyncio.create_task(
        service.execute(
            Task.model_validate_json((EXAMPLE / "task.json").read_text()),
            strategy_id="project-planning",
        )
    )
    await asyncio.wait_for(cleanup_started.wait(), timeout=2)
    worker.cancel()
    allow_cleanup.set()
    sealed = await worker
    assert sealed.status == RunStatus.CANCELLED
    assert set(runtime.closed) == {"planner", "executor", "critic"}
    await storage.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["instance_id", "output_schema"])
async def test_rejected_runtime_envelope_is_kept_as_untrusted_trace(tmp_path, field):
    class WrongEnvelopeRuntime(ScriptedRuntime):
        async def invoke(self, agent, message, context):
            result = await super().invoke(agent, message, context)
            if agent.node_id == "executor":
                if field == "instance_id":
                    result.instance_id = "foreign-instance"
                else:
                    result.output_schema = AssetRef(id="wrong-schema", version="1")
            return result

    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'rejected.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_strategy())
    sealed = await build_application(runtime=WrongEnvelopeRuntime(), storage=ports).tasks.execute(
        Task.model_validate_json((EXAMPLE / "task.json").read_text()),
        strategy_id="project-planning",
    )
    assert sealed.status == RunStatus.FAILED
    snapshot = await ports.runs.read_snapshot(sealed.run_id)
    assert len(snapshot.run.results) == 1
    trace = await ports.runs.events_for_run(sealed.run_id)
    failure = next(e for e in trace if e.event_type == EventType.AGENT_FAILED)
    assert "rejected_result" in failure.payload
    await storage.close()
