"""The finite N4 experiment is isolated and cannot fabricate an evolution trigger."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evoteam.bootstrap import build_v0_strategy
from evoteam.domain.common import AssetRef
from evoteam.domain.dataset import DatasetManifest
from evoteam.domain.planning import ANALYSIS_SCHEMA, PLAN_SCHEMA, REVIEW_SCHEMA
from evoteam.domain.role import RoleType
from evoteam.domain.run import RunPurpose
from evoteam.domain.strategy import Strategy
from evoteam.runtime.fake import FakeRuntime, ScriptedOutput

ROOT = Path(__file__).parents[1]


def prepared():
    strategy = build_v0_strategy(model_ref=AssetRef(id="fake", version="1"))
    data = strategy.model_dump()
    data["metadata"]["status"] = "current"
    for agent in data["definition"]["agents"]:
        agent["runtime_config"]["timeout_seconds"] = 5
    data["definition"]["orchestration"]["budget"] = {
        "max_tokens": 10000,
        "max_tool_calls": 0,
        "timeout_seconds": 30,
    }
    config = {
        "experiment_id": "test-n4",
        "phase": "comparison",
        "approved_scope": "fixed_candidates_offline_only",
        "dataset_ref": {"id": "project-planning-history", "version": "2"},
        "validation_plan": {
            "dataset_ref": {"id": "project-planning-validation", "version": "1"},
            "evaluator_ref": {"id": "project-planning-rules", "version": "1"},
            "repeats": 1,
            "seeds": [7],
        },
        "final_test_ref": {"id": "project-planning-final-test", "version": "1"},
        "maximum_model_requests": 50,
        "gate_policy": {
            "ref": {"id": "test-gate", "version": "1"},
            "minimum_quality_gain": 0,
            "maximum_quality_regression": 0,
            "maximum_token_increase": 0.25,
            "maximum_latency_increase": 0.5,
            "minimum_paired_runs": 6,
            "minimum_independent_tasks": 6,
            "maximum_subclass_success_regression": 0,
        },
        "monitor_policy": json.loads(
            (ROOT / "examples/experiments/n4_monitor_policy_after_baseline.json").read_text()
        ),
    }
    return SimpleNamespace(
        config=config,
        manifest=DatasetManifest.model_validate_json(
            (ROOT / "examples/datasets/project_planning_manifest.json").read_text()
        ),
        strategy=Strategy.model_validate(data),
        snapshot={"source_kind": "fixture", "code_commit": "test-only"},
        model=None,
    )


def runtime():
    return FakeRuntime(
        {
            RoleType.PLANNER: ScriptedOutput(
                ANALYSIS_SCHEMA, {"summary": "fixture", "constraint_refs": []}
            ),
            RoleType.EXECUTOR: ScriptedOutput(
                PLAN_SCHEMA, json.loads((ROOT / "examples/project_planning/plan.json").read_text())
            ),
            RoleType.CRITIC: ScriptedOutput(REVIEW_SCHEMA, {"passed": True, "issues": []}),
            RoleType.VERIFIER: ScriptedOutput(REVIEW_SCHEMA, {"passed": True, "issues": []}),
        }
    )


@pytest.mark.asyncio
async def test_campaign_keeps_paired_and_final_evidence_isolated(tmp_path):
    from evoteam.n4_campaign import execute_campaign

    result = await execute_campaign(prepared(), tmp_path, runtime())
    assert result["status"] == "completed"
    assert len(result["comparisons"]) == 2
    assert result["promoted"] is None
    assert result["serving_after"] == result["serving_before"]
    assert result["requests_used"] <= 50
    assert len(result["final_test_run_ids"]) == 2
    all_runs = result["runs"]
    ids = set(result["final_test_run_ids"])
    assert all(r["purpose"] == RunPurpose.FINAL_TEST for r in all_runs if r["run_id"] in ids)
    assert not any(
        ids & set(c["validation"]["candidate_run_ids"] + c["validation"]["current_run_ids"])
        for c in result["comparisons"]
    )
    assert all(r["dataset_source"] is not None for r in all_runs)
    assert result["monitor"]["sample_count"] == 6
    assert result["metrics_by_purpose"]["online"]["total_count"] == 6
    assert result["metrics_by_purpose"]["validation"]["total_count"] == 8
    assert result["metrics_by_purpose"]["final_test"]["total_count"] == 2
    assert all(c["gate"]["decision"] != "pass" for c in result["comparisons"])
    assert (tmp_path / "campaign_report.json").exists()
    assert len(result["snapshots"]) == len(all_runs)


@pytest.mark.asyncio
async def test_campaign_rejects_insufficient_cap_before_runtime(tmp_path):
    from evoteam.n4_campaign import execute_campaign

    p = prepared()
    p.config["maximum_model_requests"] = 49
    with pytest.raises(ValueError, match="请求上限"):
        await execute_campaign(p, tmp_path, runtime())
    assert not (tmp_path / "evidence.db").exists()


@pytest.mark.asyncio
async def test_cancelled_campaign_archives_run_and_never_opens_final_test(tmp_path):
    import asyncio

    from evoteam.n4_campaign import execute_campaign

    class CancellingRuntime(FakeRuntime):
        async def invoke(self, agent, message, context):
            raise asyncio.CancelledError()

    delegate = CancellingRuntime(runtime().outputs)
    with pytest.raises(asyncio.CancelledError):
        await execute_campaign(prepared(), tmp_path, delegate)
    report = json.loads((tmp_path / "campaign_report.json").read_text())
    assert report["status"] == "cancelled"
    assert report["requests_used"] == 1
    assert len(report["runs"]) == 1
    assert report["runs"][0]["status"] == "cancelled"
    assert report["final_test_run_ids"] == []


@pytest.mark.asyncio
async def test_campaign_cannot_reuse_existing_evidence_database(tmp_path):
    from evoteam.n4_campaign import execute_campaign

    await execute_campaign(prepared(), tmp_path, runtime())
    before = (tmp_path / "campaign_report.json").read_bytes()
    with pytest.raises(ValueError, match="存在"):
        await execute_campaign(prepared(), tmp_path, runtime())
    assert (tmp_path / "campaign_report.json").read_bytes() == before
