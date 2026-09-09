"""项目规划 v1 契约：相对整数小时、独占人员、不可拆分工作、整数货币单位。"""

from graphlib import TopologicalSorter
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from evoteam.domain.common import AssetRef, FrozenModel, Identifier
from evoteam.domain.task import Task, TaskType

Hour = Annotated[int, Field(strict=True, ge=0)]
Duration = Annotated[int, Field(strict=True, gt=0)]
Money = Annotated[int, Field(strict=True, ge=0)]
INPUT_SCHEMA = AssetRef(id="project-planning-input", version="1")
AGENT_INPUT_SCHEMA = AssetRef(id="planning-agent-input", version="1")
PLAN_SCHEMA = AssetRef(id="project-plan", version="1")
ANALYSIS_SCHEMA = AssetRef(id="planning-analysis", version="1")
REVIEW_SCHEMA = AssetRef(id="planning-review", version="1")


def unique(values: tuple[str, ...], name: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{name} 必须唯一")


class Person(FrozenModel):
    person_id: Identifier
    skills: tuple[Identifier, ...]
    hourly_cost_minor: Money
    available_from_hour: Hour
    available_until_hour: Hour

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        if self.available_until_hour <= self.available_from_hour:
            raise ValueError("人员可用区间必须为正")
        return self


class WorkItem(FrozenModel):
    work_id: Identifier
    description: Identifier
    duration_hours: Duration
    required_skills: tuple[Identifier, ...]
    dependencies: tuple[Identifier, ...]


class Milestone(FrozenModel):
    milestone_id: Identifier
    work_ids: tuple[Identifier, ...] = Field(min_length=1)
    deadline_hour: Hour


class PlanningInput(FrozenModel):
    goal: Identifier
    deadline_hour: Hour
    budget_minor: Money
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    people: tuple[Person, ...] = Field(min_length=1)
    work_items: tuple[WorkItem, ...] = Field(min_length=1)
    milestones: tuple[Milestone, ...]

    @model_validator(mode="after")
    def check_references(self) -> Self:
        unique(tuple(p.person_id for p in self.people), "person_id")
        unique(tuple(w.work_id for w in self.work_items), "work_id")
        unique(tuple(m.milestone_id for m in self.milestones), "milestone_id")
        known = {w.work_id for w in self.work_items}
        for work in self.work_items:
            unique(work.dependencies, "dependencies")
            if not set(work.dependencies) <= known:
                raise ValueError("依赖引用了未知工作项")
        tuple(
            TopologicalSorter({w.work_id: w.dependencies for w in self.work_items}).static_order()
        )
        for milestone in self.milestones:
            unique(milestone.work_ids, "milestone work_ids")
            if not set(milestone.work_ids) <= known:
                raise ValueError("里程碑引用了未知工作项")
        return self


class ScheduledWork(FrozenModel):
    work_id: Identifier
    person_id: Identifier
    start_hour: Hour
    end_hour: Hour

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        if self.end_hour <= self.start_hour:
            raise ValueError("工作区间必须为正")
        return self


class ScheduledMilestone(FrozenModel):
    milestone_id: Identifier
    completion_hour: Hour


class ProjectPlan(FrozenModel):
    schedule: tuple[ScheduledWork, ...]
    milestones: tuple[ScheduledMilestone, ...]
    risks: tuple[Identifier, ...]
    adjustments: tuple[Identifier, ...]
    validation_notes: tuple[Identifier, ...] = Field(min_length=1)


class PlanningAnalysis(FrozenModel):
    summary: Identifier
    constraint_refs: tuple[Identifier, ...]


class PlanningReview(FrozenModel):
    passed: bool
    issues: tuple[Identifier, ...]

    @model_validator(mode="after")
    def consistent_verdict(self) -> Self:
        if self.passed == bool(self.issues):
            raise ValueError("passed 与 issues 必须一致")
        return self


def parse_planning_task(task: Task) -> PlanningInput:
    if task.task_type != TaskType.PROJECT_PLANNING or task.input_schema != INPUT_SCHEMA:
        raise ValueError("仅支持 project-planning-input@1 项目规划任务")
    return PlanningInput.model_validate(task.inputs)


class PlanningAgentInput(FrozenModel):
    """节点输入信封：原 Task 与直属上游输出，来源另由 AgentMessage 保存。"""

    task: Task
    upstream: dict[str, JsonValue]
