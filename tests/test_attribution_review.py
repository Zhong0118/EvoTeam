"""Regression evidence for attribution and bounded candidate generation."""

import json

import pytest
from test_evolution import EXAMPLE, PromptSensitiveRuntime, configured_current, failure_evidence

from evoteam.composition import StoreEventSink
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.experience import AttributionKind
from evoteam.domain.run import RunPurpose
from evoteam.domain.task import Task
from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.orchestration.orchestrator import Orchestrator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.storage.sqlite import SQLiteStorage


def policy():
    return EvolutionPolicy(
        ref=AssetRef(id="test", version="1"),
        window_size=2,
        min_samples=2,
        repeated_failure_threshold=2,
        quality_drop_threshold=0.1,
        cost_overrun_threshold=0.1,
        low_contribution_threshold=0.1,
        cooldown_runs=1,
        max_candidates=2,
        stable_window_count=2,
    )


@pytest.mark.asyncio
async def test_index_without_snapshot_is_not_causal_evidence():
    report = await OutcomeAttributor().analyze_failure(failure_evidence(configured_current()))
    assert report.needs_more_evidence
    assert not report.claims


class ReviewRuntime(PromptSensitiveRuntime):
    def __init__(self, *, planner_fails=False, critic_passed=True):
        super().__init__()
        self.planner_fails = planner_fails
        self.critic_passed = critic_passed

    async def invoke(self, agent, message, context):
        if self.planner_fails and agent.node_id == "planner":
            raise RuntimeError("planner unavailable")
        result = await super().invoke(agent, message, context)
        if agent.node_id == "critic":
            result.output = {
                "passed": self.critic_passed,
                "issues": [] if self.critic_passed else ["resource conflict"],
            }
        return result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "planner_fails,critic_passed,expected",
    [
        (True, True, set()),
        (False, False, {AttributionKind.ORIGIN}),
        (False, True, {AttributionKind.ORIGIN, AttributionKind.CONTROL}),
    ],
)
async def test_attribution_uses_actual_executor_and_critic_results(
    tmp_path, planner_fails, critic_passed, expected
):
    storage = SQLiteStorage(f"sqlite:///{tmp_path / 'evidence.db'}")
    await storage.initialize()
    ports = await storage.open()
    current = configured_current()
    await ports.strategies.save(current)
    task = Task.model_validate(json.loads((EXAMPLE / "task.json").read_text()))
    runtime = ReviewRuntime(planner_fails=planner_fails, critic_passed=critic_passed)
    run = await Orchestrator(runtime, StoreEventSink(ports.runs)).execute(
        task, TaskAnalyzer().analyze(task), current, run_id="actual", purpose=RunPurpose.ONLINE
    )
    evaluation = await ProjectPlanningEvaluator().evaluate(task, run)
    sealed = await ports.runs.seal_run(task, run, evaluation, task_scope="project_planning")
    attributor = OutcomeAttributor(ports.runs)
    report = await attributor.analyze_failure((sealed,))
    assert {claim.kind for claim in report.claims} == expected
    assert report.needs_more_evidence is (not expected)
    if expected:
        generator = CandidateGenerator()
        proposals = await generator.propose(current, report, policy())
        if critic_passed:
            verifier_proposal = proposals[-1]
            new_report = report.model_copy(update={"report_id": "other-evidence"})
            other = await generator.propose(current, new_report, policy())
            assert verifier_proposal.proposal_id != other[-1].proposal_id
            candidate = generator.materialize(
                current,
                verifier_proposal,
                candidate_ref=StrategyRef(strategy_id=current.metadata.ref.strategy_id, version=1),
            )
            next_report = report.model_copy(update={"strategy": candidate.metadata.ref})
            next_proposals = await generator.propose(candidate, next_report, policy())
            assert all(proposal.target != "verifier" for proposal in next_proposals)
    await storage.close()
