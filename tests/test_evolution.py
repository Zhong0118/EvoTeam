"""首版 Prompt 自演进闭环；全部使用本地 Runtime，不调用模型 API。"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from evoteam.bootstrap import build_v0_strategy
from evoteam.composition import StoreEventSink
from evoteam.domain.agent import AgentResult
from evoteam.domain.common import AssetRef
from evoteam.domain.evaluation import EvaluationIssue, EvaluationResult, RunMetrics
from evoteam.domain.evolution import (
    EvolutionTrigger,
    MutationProposal,
    MutationType,
    TriggerType,
    ValidationPlan,
    ValidationResult,
)
from evoteam.domain.run import RunPurpose, RunStatus, SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.domain.task import Task
from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.datasets import InMemoryValidationDatasets, PackagedValidationDatasets
from evoteam.evolution.gate import GatePolicy, ValidationGate
from evoteam.evolution.lifecycle import StrategyLifecycle
from evoteam.evolution.manager import EvolutionManager
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import Validator
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.runtime.protocol import RuntimeAgent
from evoteam.storage.sqlite import SQLiteStorage

EXAMPLE = Path(__file__).parents[1] / "examples" / "project_planning"


def test_packaged_validation_dataset_resolves_by_versioned_reference():
    tasks = PackagedValidationDatasets().load(
        AssetRef(id="project-planning-validation", version="1")
    )
    assert tuple(task.task_id for task in tasks) == ("validation-resource-sequence",)


def configured_current() -> Strategy:
    data = build_v0_strategy(model_ref=AssetRef(id="fake", version="1")).model_dump()
    data["metadata"]["status"] = "current"
    data["definition"]["orchestration"]["budget"] = {
        "max_tokens": 100,
        "max_tool_calls": 0,
        "timeout_seconds": 2,
    }
    for agent in data["definition"]["agents"]:
        agent["runtime_config"]["timeout_seconds"] = 1
    return Strategy.model_validate(data)


class PromptSensitiveRuntime:
    """v0 Executor 返回冲突计划，新 Prompt 返回合法计划。"""

    def __init__(self) -> None:
        self.configs = {}
        self.messages = []

    async def create_agent(self, config, *, run_id):
        handle = RuntimeAgent(
            handle_id=f"{run_id}:{config.node_id}", run_id=run_id, node_id=config.node_id
        )
        self.configs[handle.handle_id] = config
        return handle

    async def invoke(self, agent, message, context):
        self.messages.append(message)
        config = self.configs[agent.handle_id]
        good_plan = json.loads((EXAMPLE / "plan.json").read_text())
        bad_plan = {
            **good_plan,
            "schedule": [
                {"work_id": "design", "person_id": "alice", "start_hour": 0, "end_hour": 2},
                {"work_id": "build", "person_id": "alice", "start_hour": 1, "end_hour": 5},
            ],
            "milestones": [{"milestone_id": "delivery", "completion_hour": 5}],
        }
        outputs = {
            "planner": (
                AssetRef(id="planning-analysis", version="1"),
                {"summary": "按依赖执行", "constraint_refs": []},
            ),
            "executor": (
                AssetRef(id="project-plan", version="1"),
                good_plan if config.prompt_ref.version == "v1-resource-check" else bad_plan,
            ),
            "critic": (
                AssetRef(id="planning-review", version="1"),
                {"passed": True, "issues": []},
            ),
            "verifier": (
                AssetRef(id="planning-review", version="1"),
                {"passed": True, "issues": []},
            ),
        }
        schema, output = outputs[agent.node_id]
        return AgentResult(
            instance_id=agent.handle_id,
            output_schema=schema,
            output=output,
            input_tokens=1,
            output_tokens=1,
        )

    async def close(self, agent):
        self.configs.pop(agent.handle_id)


def failure_evidence(current: Strategy) -> tuple[SealedRun, ...]:
    result = []
    for index in range(2):
        run_id = f"history-{index}"
        result.append(
            SealedRun(
                run_id=run_id,
                task_id=f"history-task-{index}",
                task_scope="project_planning",
                strategy=current.metadata.ref,
                purpose=RunPurpose.ONLINE,
                status=RunStatus.COMPLETED,
                sealed_at=datetime.now(UTC),
                snapshot_ref=f"snapshot-{index}",
                trace_refs=(),
                evaluation=EvaluationResult(
                    run_id=run_id,
                    evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
                    metrics=RunMetrics(success=False, hard_constraint_errors=1),
                    issues=(
                        EvaluationIssue(
                            code="resource_conflict",
                            message="同一人员存在重叠工作",
                            severity="error",
                        ),
                    ),
                ),
            )
        )
    return tuple(result)


@pytest.mark.asyncio
async def test_prompt_evolution_promotes_only_after_paired_validation(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'evolution.db'}")
    await storage.initialize()
    ports = await storage.open()
    current = configured_current()
    await ports.strategies.save(current)
    task = Task.model_validate_json((EXAMPLE / "task.json").read_text())
    runtime = PromptSensitiveRuntime()
    analyzer = TaskAnalyzer()
    orchestrator = Orchestrator(runtime, StoreEventSink(ports.runs))
    evaluator = ProjectPlanningEvaluator()
    validator = Validator(
        orchestrator,
        evaluator,
        analyzer,
        ports.runs,
        InMemoryValidationDatasets({("held-out", "1"): (task,)}),
    )
    manager = EvolutionManager(
        attributor=OutcomeAttributor(),
        generator=CandidateGenerator(),
        validator=validator,
        gate=ValidationGate(),
        lifecycle=StrategyLifecycle(ports.strategies),
        strategies=ports.strategies,
        records=ports.evolutions,
    )
    evidence = failure_evidence(current)
    policy = EvolutionPolicy(
        ref=AssetRef(id="evolution-policy", version="1"),
        window_size=2,
        min_samples=2,
        repeated_failure_threshold=2,
        quality_drop_threshold=0.1,
        cost_overrun_threshold=0.1,
        low_contribution_threshold=0.1,
        cooldown_runs=1,
        max_candidates=1,
        stable_window_count=2,
    )
    trigger = EvolutionTrigger(
        trigger_id="trigger-resource-conflict",
        strategy=current.metadata.ref,
        policy_ref=policy.ref,
        trigger_type=TriggerType.REPEATED_FAILURE,
        task_scope="project_planning",
        evidence_run_ids=tuple(run.run_id for run in evidence),
        reason="resource_conflict 重复出现",
    )
    record = await manager.evolve(
        trigger,
        current,
        evidence,
        policy,
        ValidationPlan(
            dataset_ref=AssetRef(id="held-out", version="1"),
            evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
            repeats=1,
            seeds=(7,),
        ),
        GatePolicy(
            ref=AssetRef(id="gate", version="1"),
            minimum_quality_gain=0,
            maximum_quality_regression=0,
            maximum_token_increase=0,
            maximum_latency_increase=1000,
        ),
    )

    assert record.promoted is not None
    assert record.gate_results[0].decision.value == "pass"
    promoted = await ports.strategies.current("project-planning")
    assert promoted.metadata.ref == record.promoted
    assert promoted.metadata.status == StrategyStatus.CURRENT
    assert promoted.metadata.parent == current.metadata.ref
    executor = next(agent for agent in promoted.definition.agents if agent.node_id == "executor")
    assert executor.prompt_ref == AssetRef(id="executor", version="v1-resource-check")
    assert (
        await ports.strategies.get(current.metadata.ref)
    ).metadata.status == StrategyStatus.RETIRED
    assert await ports.evolutions.get_record(record.evolution_id) == record
    assert len(record.validation_refs) == 1
    assert (
        len(
            await ports.runs.recent_runs(
                current.metadata.ref,
                task_scope="project_planning",
                purpose=RunPurpose.VALIDATION,
                limit=10,
            )
        )
        == 1
    )
    assert (
        await ports.runs.recent_runs(
            current.metadata.ref,
            task_scope="project_planning",
            purpose=RunPurpose.ONLINE,
            limit=10,
        )
        == ()
    )
    await storage.close()


@pytest.mark.asyncio
async def test_sqlite_allocates_unique_candidate_versions(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'versions.db'}")
    await storage.initialize()
    ports = await storage.open()
    await ports.strategies.save(configured_current())
    first = await ports.strategies.allocate_version("project-planning")
    second = await ports.strategies.allocate_version("project-planning")
    assert (first.version, second.version) == (1, 2)
    await storage.close()


@pytest.mark.asyncio
async def test_verifier_candidate_executes_restricted_dag_with_provenance(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'verifier.db'}")
    await storage.initialize()
    ports = await storage.open()
    current = configured_current()
    await ports.strategies.save(current)
    proposal = MutationProposal(
        proposal_id="add-verifier",
        parent=current.metadata.ref,
        operation=MutationType.ADD_AGENT_CONFIG,
        target="verifier",
        rationale="独立复核",
        attribution_ref="attribution",
        replacement_ref=AssetRef(id="verifier", version="v0"),
    )
    candidate_ref = await ports.strategies.allocate_version("project-planning")
    candidate = CandidateGenerator().materialize(current, proposal, candidate_ref=candidate_ref)
    await ports.strategies.save(candidate)
    runtime = PromptSensitiveRuntime()
    task = Task.model_validate_json((EXAMPLE / "task.json").read_text())
    run = await Orchestrator(runtime, StoreEventSink(ports.runs)).execute(
        task,
        TaskAnalyzer().analyze(task),
        candidate,
        run_id="verifier-dag",
        purpose=RunPurpose.VALIDATION,
    )
    assert run.status == RunStatus.COMPLETED
    assert run.team is not None
    assert [instance.config.node_id for instance in run.team.instances] == [
        "planner",
        "executor",
        "verifier",
        "critic",
    ]
    critic_message = runtime.messages[-1]
    assert set(critic_message.payload["upstream"]) == {"executor", "verifier"}
    assert len(critic_message.source_event_ids) == 2
    await storage.close()


class ControlledValidator:
    """为多候选选择提供确定性配对指标，不调用模型。"""

    async def validate(self, current, candidate, plan):
        has_verifier = any(agent.role.value == "verifier" for agent in candidate.definition.agents)
        return ValidationResult(
            validation_id=f"validation-{candidate.metadata.ref.version}",
            current=current.metadata.ref,
            candidate=candidate.metadata.ref,
            plan=plan,
            current_run_ids=(f"current-{candidate.metadata.ref.version}",),
            candidate_run_ids=(f"candidate-{candidate.metadata.ref.version}",),
            current_metrics=RunMetrics(
                success=False, hard_constraint_errors=1, tokens=100, latency_seconds=2
            ),
            candidate_metrics=RunMetrics(
                success=True,
                hard_constraint_errors=0,
                tokens=70 if has_verifier else 80,
                latency_seconds=1,
            ),
        )


@pytest.mark.asyncio
async def test_multiple_candidates_select_one_and_persist_full_artifacts(tmp_path):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'multi.db'}")
    await storage.initialize()
    ports = await storage.open()
    current = configured_current()
    await ports.strategies.save(current)
    manager = EvolutionManager(
        attributor=OutcomeAttributor(),
        generator=CandidateGenerator(),
        validator=ControlledValidator(),
        gate=ValidationGate(),
        lifecycle=StrategyLifecycle(ports.strategies),
        strategies=ports.strategies,
        records=ports.evolutions,
    )
    evidence = failure_evidence(current)
    policy = EvolutionPolicy(
        ref=AssetRef(id="multi-policy", version="1"),
        window_size=2,
        min_samples=2,
        repeated_failure_threshold=2,
        quality_drop_threshold=0.1,
        cost_overrun_threshold=0.1,
        low_contribution_threshold=0.1,
        cooldown_runs=0,
        max_candidates=2,
        stable_window_count=2,
    )
    trigger = EvolutionTrigger(
        trigger_id="multi-trigger",
        strategy=current.metadata.ref,
        policy_ref=policy.ref,
        trigger_type=TriggerType.REPEATED_FAILURE,
        task_scope="project_planning",
        evidence_run_ids=tuple(run.run_id for run in evidence),
        reason="resource_conflict 重复出现",
    )
    plan = ValidationPlan(
        dataset_ref=AssetRef(id="held-out", version="1"),
        evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
        repeats=1,
        seeds=(1,),
    )
    record = await manager.evolve(
        trigger,
        current,
        evidence,
        policy,
        plan,
        GatePolicy(
            ref=AssetRef(id="gate", version="multi"),
            minimum_quality_gain=0,
            maximum_quality_regression=0,
            maximum_token_increase=0,
            maximum_latency_increase=0,
        ),
    )

    assert len(record.candidates) == len(record.proposal_refs) == len(record.gate_results) == 2
    assert record.promoted == record.candidates[1]
    assert (await ports.strategies.get(record.candidates[0])).metadata.status.value == "rejected"
    promoted = await ports.strategies.get(record.candidates[1])
    assert promoted.metadata.status.value == "current"
    assert any(agent.role.value == "verifier" for agent in promoted.definition.agents)
    assert (await ports.strategies.get(current.metadata.ref)).metadata.status.value == "retired"
    for ref in record.attribution_refs:
        assert (await ports.evolutions.get_attribution(ref)).report_id == ref
    for ref in record.proposal_refs:
        assert (await ports.evolutions.get_proposal(ref)).proposal_id == ref
    for ref in record.validation_refs:
        assert (await ports.evolutions.get_validation(ref)).validation_id == ref
    assert await ports.evolutions.get_record(record.evolution_id) == record
    await storage.close()
