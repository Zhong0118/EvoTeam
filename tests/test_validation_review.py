"""不允许候选通过额外预算或不同模型取得对照优势。"""

import json

import pytest
from test_evolution import EXAMPLE, configured_current

from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.evolution import MutationProposal, MutationType, ValidationPlan
from evoteam.domain.task import Task
from evoteam.evolution.datasets import InMemoryValidationDatasets
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import Validator


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["budget", "model", "runtime"])
async def test_validation_rejects_unfair_candidate_before_execution(changed):
    current = configured_current()
    candidate = CandidateGenerator().materialize(
        current,
        MutationProposal(
            proposal_id="prompt",
            parent=current.metadata.ref,
            operation=MutationType.UPDATE_PROMPT,
            target="executor",
            rationale="check",
            attribution_ref="history",
            replacement_ref=AssetRef(id="executor", version="v1-resource-check"),
        ),
        candidate_ref=StrategyRef(strategy_id=current.metadata.ref.strategy_id, version=1),
    )
    data = candidate.model_dump()
    if changed == "budget":
        data["definition"]["orchestration"]["budget"]["max_tokens"] += 100
    elif changed == "model":
        data["definition"]["agents"][1]["model_ref"]["version"] = "different"
    else:
        data["definition"]["agents"][1]["runtime_config"]["timeout_seconds"] += 10
    candidate = type(candidate).model_validate(data)
    task = Task.model_validate(json.loads((EXAMPLE / "task.json").read_text()))

    class NeverExecute:
        async def execute(self, *args, **kwargs):
            pytest.fail("不公平候选不应启动 Runtime")

    from typing import cast

    from evoteam.evaluation.evaluator import Evaluator
    from evoteam.orchestration.orchestrator import Orchestrator
    from evoteam.orchestration.task_analyzer import TaskAnalyzer
    from evoteam.storage.protocol import RunStore

    validator = Validator(
        cast(Orchestrator, NeverExecute()),
        cast(Evaluator, None),
        TaskAnalyzer(),
        cast(RunStore, None),
        InMemoryValidationDatasets({("held-out", "1"): (task,)}),
    )
    with pytest.raises(ValueError, match="比较"):
        await validator.validate(
            current,
            candidate,
            ValidationPlan(
                dataset_ref=AssetRef(id="held-out", version="1"),
                evaluator_ref=AssetRef(id="project-planning-rules", version="1"),
                repeats=1,
                seeds=(1,),
            ),
        )
