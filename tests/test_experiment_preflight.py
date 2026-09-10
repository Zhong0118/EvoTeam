import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import SecretStr

from evoteam import experiment
from evoteam.settings import Settings


@pytest.fixture
def inputs(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    source = Path(__file__).resolve().parents[1]
    shutil.copytree(source / "examples", repository / "examples")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.org",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=repository,
        check=True,
    )
    settings = Settings(
        model_id="default-model",
        model_version="1",
        model_name="test-model",
        model_base_url="https://example.org",
        model_api_key=SecretStr("do-not-persist"),
        model_timeout_seconds=30,
        model_max_output_tokens=1024,
        model_temperature=0,
        model_top_p=1,
    )
    config_path = repository / "examples/experiments/n4_baseline_v0.json"
    config = json.loads(config_path.read_text())
    strategy_path = repository / config["strategy_file"]
    strategy = json.loads(strategy_path.read_text())
    ref = strategy["definition"]["agents"][0]["model_ref"]
    settings.model_id = ref["id"]
    settings.model_version = ref["version"]
    config.pop("expected_model", None)
    external_config = tmp_path / "config.json"
    external_config.write_text(json.dumps(config))
    return repository, external_config, tmp_path / "output", settings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ref", [{"id": "wrong", "version": "1"}, {"id": "project-planning-rules", "version": "2"}]
)
async def test_baseline_rejects_wrong_evaluator_before_runtime(inputs, monkeypatch, ref):
    repository, path, output, settings = inputs
    config = json.loads(path.read_text())
    config["evaluator_ref"] = ref
    path.write_text(json.dumps(config))

    def forbidden(*args, **kwargs):
        pytest.fail("runtime created before evaluator was validated")

    monkeypatch.setattr(experiment, "OpenJiuwenRuntimeAdapter", forbidden)
    with pytest.raises(ValueError, match="评价器"):
        await experiment.run_baseline(repository, path, output, settings)
    assert not output.exists()


@pytest.mark.asyncio
async def test_baseline_rejects_model_parameters_before_runtime(inputs, monkeypatch):
    repository, path, output, settings = inputs
    config = json.loads(path.read_text())
    config["expected_model"] = {
        "ref": {"id": settings.model_id, "version": settings.model_version},
        "model_name": "test-model",
        "temperature": 1,
        "top_p": 1,
        "max_output_tokens": 1024,
        "timeout_seconds": 30,
    }
    path.write_text(json.dumps(config))
    monkeypatch.setattr(
        experiment,
        "OpenJiuwenRuntimeAdapter",
        lambda **kwargs: pytest.fail("runtime created before model was validated"),
    )
    with pytest.raises(ValueError, match="模型"):
        await experiment.run_baseline(repository, path, output, settings)


@pytest.mark.asyncio
async def test_snapshot_precedes_runtime_and_survives_cancel(inputs, monkeypatch):
    import asyncio

    repository, path, output, settings = inputs
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    def cancel(**kwargs):
        snapshot = json.loads((output / "preflight.json").read_text())
        assert snapshot["config_sha256"] == original_hash
        assert snapshot["code_dirty"] is False
        assert snapshot["prompt_sources"]
        path.write_text("{}")
        raise asyncio.CancelledError()

    monkeypatch.setattr(experiment, "OpenJiuwenRuntimeAdapter", cancel)
    with pytest.raises(asyncio.CancelledError):
        await experiment.run_baseline(repository, path, output, settings)
    report = json.loads((output / "baseline_report.json").read_text())
    assert report["status"] == "cancelled"
    assert report["config_sha256"] == original_hash
    assert report["runs"] == []
    assert "do-not-persist" not in (output / "preflight.json").read_text()
    with pytest.raises(ValueError, match="存在"):
        await experiment.run_baseline(repository, path, output, settings)


@pytest.mark.asyncio
async def test_dirty_tracked_tree_rejected_before_runtime(inputs, monkeypatch):
    repository, path, output, settings = inputs
    (repository / "examples/experiments/n4_baseline_v0.json").write_text("{}")
    monkeypatch.setattr(
        experiment,
        "OpenJiuwenRuntimeAdapter",
        lambda **kwargs: pytest.fail("runtime created on dirty tree"),
    )
    with pytest.raises(ValueError, match="未提交"):
        await experiment.run_baseline(repository, path, output, settings)


@pytest.mark.asyncio
async def test_failure_report_preserves_completed_runs_without_sdk_error(inputs, monkeypatch):
    from types import SimpleNamespace

    repository, path, output, settings = inputs

    class Tasks:
        calls = 0

        async def execute(self, task, *, strategy_id, dataset_source):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("SDK key=do-not-persist")
            return SimpleNamespace(
                status="succeeded", model_dump=lambda **kwargs: {"run_id": "completed-first"}
            )

    monkeypatch.setattr(experiment, "OpenJiuwenRuntimeAdapter", lambda **kwargs: object())
    monkeypatch.setattr(
        experiment, "build_application", lambda **kwargs: SimpleNamespace(tasks=Tasks())
    )
    with pytest.raises(RuntimeError):
        await experiment.run_baseline(repository, path, output, settings)
    content = (output / "baseline_report.json").read_text()
    report = json.loads(content)
    assert report["status"] == "failed"
    assert report["runs"] == [{"run_id": "completed-first"}]
    assert "SDK key" not in content
    assert "do-not-persist" not in content


@pytest.mark.asyncio
async def test_cancelled_sealed_run_stops_baseline_and_is_preserved(inputs, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from evoteam.domain.run import RunStatus

    repository, path, output, settings = inputs

    class Tasks:
        async def execute(self, task, **kwargs):
            return SimpleNamespace(
                status=RunStatus.CANCELLED,
                model_dump=lambda **kwargs: {"run_id": "cancelled-first", "status": "cancelled"},
            )

    monkeypatch.setattr(experiment, "OpenJiuwenRuntimeAdapter", lambda **kwargs: object())
    monkeypatch.setattr(
        experiment, "build_application", lambda **kwargs: SimpleNamespace(tasks=Tasks())
    )
    with pytest.raises(asyncio.CancelledError):
        await experiment.run_baseline(repository, path, output, settings)
    report = json.loads((output / "baseline_report.json").read_text())
    assert report["status"] == "cancelled"
    assert report["runs"] == [{"run_id": "cancelled-first", "status": "cancelled"}]


@pytest.mark.asyncio
async def test_prepared_baseline_validation_failure_has_terminal_report(inputs):
    repository, path, output, settings = inputs
    config = json.loads(path.read_text())
    config["expected_task_count"] = 999
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="任务数量"):
        await experiment.run_baseline(repository, path, output, settings)
    report = json.loads((output / "baseline_report.json").read_text())
    assert report["status"] == "failed"
    assert report["requests_used"] == 0
    assert report["runs"] == []
