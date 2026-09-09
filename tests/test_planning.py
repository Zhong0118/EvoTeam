"""确定性正反例：防止自然语言审查掩盖硬约束错误。"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evoteam.domain.agent import AgentResult
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.run import RunPurpose, RunResult, RunStatus
from evoteam.domain.task import Task
from evoteam.evaluation.evaluator import ProjectPlanningEvaluator
from evoteam.orchestration.task_analyzer import TaskAnalyzer
from evoteam.tools.constraint_checker import ConstraintChecker

EXAMPLE = Path(__file__).parents[1] / "examples" / "project_planning"


def task_data():
    return json.loads((EXAMPLE / "task.json").read_text())


def plan_data():
    return json.loads((EXAMPLE / "plan.json").read_text())


def test_adjacent_intervals_and_exact_budget_are_valid():
    data = task_data()
    data["inputs"]["budget_minor"] = 600
    assert ConstraintChecker().check(Task.model_validate(data), plan_data()) == ()
    profile = TaskAnalyzer().analyze(Task.model_validate(data))
    assert "delivery" in profile.constraint_refs


@pytest.mark.parametrize(
    "case, expected",
    [
        ("overlap", "resource_conflict"),
        ("dependency", "dependency_order"),
        ("duration", "duration_mismatch"),
        ("missing", "missing_work"),
        ("duplicate", "duplicate_work"),
        ("unknown", "unknown_person"),
        ("skills", "missing_skill"),
        ("availability", "outside_availability"),
        ("deadline", "project_deadline"),
        ("budget", "budget_exceeded"),
        ("milestone", "milestone_completion"),
        ("missing_milestone", "missing_milestone"),
        ("schema", "output_schema"),
    ],
)
def test_hard_constraint_violations_have_locatable_evidence(case, expected):
    data, plan = task_data(), plan_data()
    if case in ("overlap", "dependency"):
        plan["schedule"][1].update(start_hour=1, end_hour=5)
    elif case == "duration":
        plan["schedule"][0]["end_hour"] = 1
    elif case == "missing":
        plan["schedule"].pop()
    elif case == "duplicate":
        plan["schedule"].append(plan["schedule"][0].copy())
    elif case == "unknown":
        plan["schedule"][0]["person_id"] = "ghost"
    elif case == "skills":
        data["inputs"]["people"][0]["skills"] = ["design"]
    elif case == "availability":
        data["inputs"]["people"][0]["available_until_hour"] = 5
    elif case == "deadline":
        data["inputs"]["deadline_hour"] = 5
    elif case == "budget":
        data["inputs"]["budget_minor"] = 599
    elif case == "milestone":
        plan["milestones"][0]["completion_hour"] = 5
    elif case == "missing_milestone":
        plan["milestones"] = []
    else:
        del plan["risks"]
    issues = ConstraintChecker().check(Task.model_validate(data), plan)
    matching = [issue for issue in issues if issue.code == expected]
    assert matching and all(issue.evidence_refs for issue in matching)


@pytest.mark.parametrize("case", ["cycle", "dangling", "duplicate", "fractional", "schema"])
def test_invalid_input_rejected_before_execution(case):
    data = task_data()
    if case == "cycle":
        data["inputs"]["work_items"][0]["dependencies"] = ["build"]
    elif case == "dangling":
        data["inputs"]["work_items"][1]["dependencies"] = ["ghost"]
    elif case == "duplicate":
        data["inputs"]["people"].append(data["inputs"]["people"][0].copy())
    elif case == "fractional":
        data["inputs"]["work_items"][0]["duration_hours"] = 1.5
    else:
        data["input_schema"]["version"] = "unknown"
    with pytest.raises((ValueError, ValidationError)):
        TaskAnalyzer().analyze(Task.model_validate(data))


@pytest.mark.asyncio
async def test_evaluator_uses_executor_plan_and_retains_partial_failure():
    task = Task.model_validate(task_data())
    result = AgentResult(
        instance_id="executor-instance",
        output_schema=AssetRef(id="project-plan", version="1"),
        output=plan_data(),
    )
    run = RunResult(
        run_id="r1",
        task_id=task.task_id,
        strategy=StrategyRef(strategy_id="project-planning", version=0),
        purpose=RunPurpose.ONLINE,
        status=RunStatus.FAILED,
        results=[result],
    )
    evaluation = await ProjectPlanningEvaluator().evaluate(task, run)
    assert evaluation.metrics.success is False
    assert evaluation.metrics.hard_constraint_errors == 0
    assert evaluation.metrics.quality is None
    assert "tokens" in evaluation.missing_metrics
    run.status = RunStatus.COMPLETED
    run.results.append(
        AgentResult(
            instance_id="critic-instance",
            output_schema=AssetRef(id="planning-review", version="1"),
            output={"passed": True, "issues": []},
        )
    )
    result.output["schedule"] = []
    evaluation = await ProjectPlanningEvaluator().evaluate(task, run)
    assert evaluation.metrics.success is False
    assert any(issue.code == "missing_work" for issue in evaluation.issues)


def test_metrics_count_results_once_despite_message_trace_repetition():
    from datetime import UTC, datetime

    from evoteam.domain.events import EventType, TraceEvent
    from evoteam.evaluation.metrics import MetricsCollector

    run = RunResult(
        run_id="metrics",
        task_id="t1",
        strategy=StrategyRef(strategy_id="project-planning", version=0),
        purpose=RunPurpose.ONLINE,
        status=RunStatus.COMPLETED,
        latency_seconds=1.5,
        tool_calls=0,
        retry_count=0,
        results=[
            AgentResult(
                instance_id="one",
                output_schema=AssetRef(id="plan", version="1"),
                output={},
                input_tokens=12,
                output_tokens=8,
            )
        ],
    )
    event = TraceEvent(
        event_id="e1",
        sequence=0,
        timestamp=datetime.now(UTC),
        event_type=EventType.AGENT_MESSAGE,
        strategy=run.strategy,
        run_id=run.run_id,
        payload={"input_tokens": 12, "output_tokens": 8},
    )
    metrics = MetricsCollector().collect(run, (event, event))
    assert metrics.tokens == 20
    assert metrics.latency_seconds == 1.5
    assert metrics.cost is None
    run.status = RunStatus.FAILED
    assert MetricsCollector().collect(run, (event,)).tokens is None
