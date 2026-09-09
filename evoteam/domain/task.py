"""用户任务与任务画像；不根据 Task 自由生成新 Strategy。"""

from enum import StrEnum

from pydantic import Field, JsonValue

from evoteam.domain.common import AssetRef, DomainModel, Identifier, RunBudget


class TaskType(StrEnum):
    PROJECT_PLANNING = "project_planning"
    REPORT_GENERATION = "report_generation"
    DATA_ANALYSIS = "data_analysis"


class Task(DomainModel):
    task_id: Identifier
    task_type: TaskType
    instruction: Identifier
    input_schema: AssetRef
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    # 项目规划信封由 planning.parse_planning_task 按固定版本解析。


class TaskProfile(DomainModel):
    task_id: Identifier
    task_type: TaskType
    required_capabilities: tuple[AssetRef, ...] = ()
    constraint_refs: tuple[str, ...] = ()
    risk_labels: tuple[str, ...] = ()
    complexity: str | None = None
    budget: RunBudget = Field(default_factory=RunBudget)
