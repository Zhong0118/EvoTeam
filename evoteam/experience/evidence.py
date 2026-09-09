"""经验与监控共用的可比较证据边界。"""

import hashlib
import json
from collections.abc import Sequence

from evoteam.domain.run import RunPurpose, RunStatus, SealedRun


def evidence_id(prefix: str, values: object) -> str:
    encoded = json.dumps(values, sort_keys=True, ensure_ascii=False, default=str).encode()
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()}"


def validate_window(runs: Sequence[SealedRun]) -> None:
    if not runs:
        return
    first = runs[0]
    if len({run.run_id for run in runs}) != len(runs):
        raise ValueError("证据窗口含重复 Run")
    for run in runs:
        if (
            run.strategy != first.strategy
            or run.task_scope != first.task_scope
            or run.purpose != RunPurpose.ONLINE
            or run.evaluation.run_id != run.run_id
            or run.evaluation.evaluator_ref != first.evaluation.evaluator_ref
            or run.status
            not in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.TIMED_OUT}
        ):
            raise ValueError("只能分析同策略、范围和评价版本的已封存线上证据")


def failure_codes(run: SealedRun) -> set[str]:
    codes = {issue.code for issue in run.evaluation.issues if issue.severity == "error"}
    if not codes and run.status != RunStatus.COMPLETED:
        codes.add(f"run_{run.status.value}")
    return codes
