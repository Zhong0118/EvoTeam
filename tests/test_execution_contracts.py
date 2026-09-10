"""F0 执行契约：提交、状态视图与增量事件信封；样例与前端共用同一 JSON 文件。"""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from evoteam.execution.models import (
    ExecutionEventsPage,
    ExecutionPhase,
    ExecutionStatus,
    ExecutionView,
    SubmitExecution,
    TraceEventView,
)

SAMPLES: dict[str, Any] = json.loads(
    (Path(__file__).parents[1] / "frontend/src/fixtures/execution-samples.json").read_text("utf-8")
)


def test_submit_valid_sample_round_trips():
    submission = SubmitExecution.model_validate(SAMPLES["submit"]["valid"])
    assert submission.task.task_id == "task-web-1"
    assert submission.task.inputs["goal"] == "网站上线"
    assert json.loads(submission.model_dump_json()) == SAMPLES["submit"]["valid"]


@pytest.mark.parametrize(
    "case",
    [
        "unknown_dependency",
        "dependency_cycle",
        "missing_milestones_field",
        "duplicate_person",
        "bad_request_id",
    ],
)
def test_submit_rejects_invalid_samples(case):
    with pytest.raises(ValidationError):
        SubmitExecution.model_validate(SAMPLES["submit"][case])


def test_submit_rejects_wrong_planning_schema_ref():
    sample = json.loads(json.dumps(SAMPLES["submit"]["valid"]))
    sample["task"]["input_schema"]["version"] = "2"
    with pytest.raises(ValidationError):
        SubmitExecution.model_validate(sample)


def test_views_parse_and_round_trip_all_samples():
    for name, sample in SAMPLES["views"].items():
        view = ExecutionView.model_validate(sample)
        assert view.status == sample["status"], name
        assert json.loads(view.model_dump_json()) == sample, name


def test_view_rejects_wrong_status_and_phase_values():
    running = SAMPLES["views"]["running"]
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**running, "status": "in_progress"})
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**running, "phase": "queued"})


def test_view_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ExecutionView.model_validate(
            {**SAMPLES["views"]["accepted"], "evaluation": {"success": False}}
        )


def test_view_lifecycle_invariants():
    success = SAMPLES["views"]["success"]
    accepted = SAMPLES["views"]["accepted"]
    interrupted = SAMPLES["views"]["interrupted"]
    # completed 表示流程完成并封存：缺少 sealed_run_id 不合法。
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**success, "sealed_run_id": None})
    # interrupted 不得伪造成一个已封存 Run。
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**interrupted, "sealed_run_id": "run-web-5"})
    # 未终态作业不能引用封存记录或记录结束时间。
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**accepted, "sealed_run_id": "run-web-1"})
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**accepted, "finished_at": success["finished_at"]})
    # accepted 作业尚未开始执行。
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**accepted, "started_at": success["started_at"]})
    # running 作业必须记录开始时间。
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**SAMPLES["views"]["running"], "started_at": None})
    # phase=terminal 必须与终态 status 一致。
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**success, "phase": "sealing"})
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**SAMPLES["views"]["running"], "phase": "terminal"})


def test_completed_is_legal_regardless_of_evaluation_result():
    view = ExecutionView.model_validate(SAMPLES["views"]["evaluation_failed"])
    assert view.status is ExecutionStatus.COMPLETED
    assert view.phase is ExecutionPhase.TERMINAL
    # 作业状态不承载评价结果；success=false 由 Run 详情页展示。
    assert "evaluation" not in SAMPLES["views"]["evaluation_failed"]


def test_last_sequence_only_allows_minus_one_without_events():
    assert ExecutionView.model_validate(SAMPLES["views"]["accepted"]).last_sequence == -1
    with pytest.raises(ValidationError):
        ExecutionView.model_validate({**SAMPLES["views"]["accepted"], "last_sequence": -2})


def test_event_pages_parse_with_ordered_sequences():
    for name, sample in SAMPLES["events"].items():
        page = ExecutionEventsPage.model_validate(sample)
        sequences = [event.sequence for event in page.items]
        assert sequences == sorted(sequences), name
    empty = ExecutionEventsPage.model_validate(SAMPLES["events"]["empty_page"])
    assert empty.items == ()
    assert empty.next_after_sequence == -1
    assert empty.terminal is False


def test_event_view_whitelists_projection_extras():
    running = SAMPLES["events"]["running_page"]
    completed = TraceEventView.model_validate(running["items"][1])
    assert completed.node_state == "completed"
    assert completed.output is not None
    team = TraceEventView.model_validate(running["items"][0])
    assert team.config is not None
    assert "context" not in (team.config or {})


def test_events_page_rejects_invalid_cursor_and_shapes():
    with pytest.raises(ValidationError):
        ExecutionEventsPage.model_validate(
            {**SAMPLES["events"]["empty_page"], "next_after_sequence": -2}
        )
    with pytest.raises(ValidationError):
        ExecutionEventsPage.model_validate({**SAMPLES["events"]["empty_page"], "extra_field": True})
