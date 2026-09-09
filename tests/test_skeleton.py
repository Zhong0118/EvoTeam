"""验证固定契约与骨架边界，不把未来业务逻辑写进测试。"""

import ast
import importlib
import json
import pkgutil
from pathlib import Path

import pytest
from pydantic import ValidationError

import evoteam
from evoteam.bootstrap import build_v0_strategy
from evoteam.cli import main
from evoteam.domain.agent import AgentConfig
from evoteam.domain.common import AssetRef
from evoteam.domain.role import ROLE_POOL, RoleType
from evoteam.domain.strategy import Strategy
from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
from evoteam.runtime.protocol import AgentRuntime


def test_v0_is_serializable_and_resolves_packaged_prompts():
    strategy = build_v0_strategy(model_ref=AssetRef(id="test-model", version="fixture"))
    restored = Strategy.model_validate_json(strategy.model_dump_json())
    assert restored == strategy
    assert tuple(node.role for node in strategy.definition.agents) == (
        RoleType.PLANNER,
        RoleType.EXECUTOR,
        RoleType.CRITIC,
    )
    assert {(edge.source, edge.target) for edge in strategy.definition.edges} == {
        ("planner", "executor"),
        ("executor", "critic"),
    }
    from evoteam.capabilities.prompts import load_prompt

    for node in strategy.definition.agents:
        assert load_prompt(node.prompt_ref).strip()


def test_unknown_role_and_runtime_context_cannot_enter_stable_config():
    config = build_v0_strategy(model_ref=AssetRef(id="test", version="1")).definition.agents[0]
    data = config.model_dump()
    with pytest.raises(ValidationError):
        AgentConfig.model_validate({**data, "role": "super_agent"})
    with pytest.raises(ValidationError):
        AgentConfig.model_validate({**data, "context": {"secret": "runtime-only"}})
    with pytest.raises(ValidationError):
        config.role = RoleType.VERIFIER
    with pytest.raises(TypeError):
        ROLE_POOL[RoleType.PLANNER] = ROLE_POOL[RoleType.CRITIC]  # type: ignore[index]


def test_prompt_loader_does_not_accept_arbitrary_paths():
    from evoteam.capabilities.prompts import load_prompt

    with pytest.raises(KeyError):
        load_prompt(AssetRef(id="../../README", version="md"))


@pytest.mark.asyncio
async def test_unconfigured_adapter_cannot_report_success():
    config = build_v0_strategy(model_ref=AssetRef(id="test", version="1")).definition.agents[0]
    runtime: AgentRuntime = OpenJiuwenRuntimeAdapter()
    with pytest.raises(ValueError, match="openJiuwen"):
        await runtime.create_agent(config, run_id="run-1")


def test_every_module_imports_without_credentials_or_sdk_side_effects():
    for module in pkgutil.walk_packages(evoteam.__path__, prefix="evoteam."):
        importlib.import_module(module.name)


def test_sdk_imports_are_confined_to_adapter():
    root = Path(evoteam.__file__).parent
    for path in root.rglob("*.py"):
        if path.is_relative_to(root / "runtime" / "openjiuwen"):
            continue
        tree = ast.parse(path.read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(name.split(".")[0] == "openjiuwen" for name in imports), path


def test_cli_exports_draft_without_claiming_ready_to_run(capsys: pytest.CaptureFixture[str]):
    assert main(["v0", "--model-id", "fixture", "--model-version", "1"]) == 0
    output = json.loads(capsys.readouterr().out)
    strategy = Strategy.model_validate(output)
    assert strategy.metadata.status.value == "draft"
    assert strategy.definition.orchestration.budget.max_tokens is None


def test_cli_requires_explicit_command_and_model_configuration():
    for arguments in ([], ["v0"], ["run"], ["evolve"]):
        with pytest.raises(SystemExit) as exc:
            main(arguments)
        assert exc.value.code == 2
