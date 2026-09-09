"""确定性项目约束；不相信 Agent 的自报成本或通过意见。"""

from collections import Counter
from itertools import combinations

from pydantic import JsonValue, ValidationError

from evoteam.domain.evaluation import EvaluationIssue
from evoteam.domain.planning import ProjectPlan, parse_planning_task
from evoteam.domain.task import Task


class ConstraintChecker:
    def check(self, task: Task, output: dict[str, JsonValue]) -> tuple[EvaluationIssue, ...]:
        spec = parse_planning_task(task)
        issues: list[EvaluationIssue] = []

        def issue(code: str, message: str, *refs: str) -> None:
            issues.append(
                EvaluationIssue(code=code, message=message, severity="error", evidence_refs=refs)
            )

        try:
            plan = ProjectPlan.model_validate(output)
        except ValidationError as exc:
            for error in exc.errors(include_input=False, include_url=False):
                path = "/".join(str(part) for part in error["loc"])
                issue("output_schema", error["msg"], f"output:/{path}")
            return tuple(issues)

        work = {w.work_id: w for w in spec.work_items}
        people = {p.person_id: p for p in spec.people}
        scheduled = {s.work_id: s for s in plan.schedule}
        for work_id, count in Counter(s.work_id for s in plan.schedule).items():
            if count > 1:
                issue("duplicate_work", "工作项重复排期", f"work:{work_id}")
        for work_id in sorted(work.keys() - scheduled.keys()):
            issue("missing_work", "必需工作项未排期", f"work:{work_id}")
        cost = 0
        cost_known = True
        for item in plan.schedule:
            ref = f"work:{item.work_id}"
            requirement = work.get(item.work_id)
            person = people.get(item.person_id)
            if requirement is None:
                issue("unknown_work", "排期引用未知工作项", ref)
            else:
                if item.end_hour - item.start_hour != requirement.duration_hours:
                    issue("duration_mismatch", "工期与输入要求不符", ref)
                for dependency in requirement.dependencies:
                    previous = scheduled.get(dependency)
                    if previous is not None and item.start_hour < previous.end_hour:
                        issue("dependency_order", "前置工作尚未完成", ref, f"work:{dependency}")
                if person and not set(requirement.required_skills) <= set(person.skills):
                    issue("missing_skill", "负责人缺少必需技能", ref, f"person:{person.person_id}")
            if person is None:
                cost_known = False
                issue("unknown_person", "排期引用未知人员", ref, f"person:{item.person_id}")
            else:
                cost += (item.end_hour - item.start_hour) * person.hourly_cost_minor
                if (
                    item.start_hour < person.available_from_hour
                    or item.end_hour > person.available_until_hour
                ):
                    issue("outside_availability", "排期超出人员可用时间", ref)
            if item.end_hour > spec.deadline_hour:
                issue("project_deadline", "超过项目期限", ref, "input:/deadline_hour")
        for left, right in combinations(plan.schedule, 2):
            if left.person_id == right.person_id and max(left.start_hour, right.start_hour) < min(
                left.end_hour, right.end_hour
            ):
                issue(
                    "resource_conflict",
                    "同一人员存在重叠工作",
                    f"work:{left.work_id}",
                    f"work:{right.work_id}",
                    f"person:{left.person_id}",
                )
        if cost_known and cost > spec.budget_minor:
            issue(
                "budget_exceeded",
                f"人工费用 {cost} 超过预算 {spec.budget_minor}",
                "output:/schedule",
                "input:/budget_minor",
            )

        milestones = {m.milestone_id: m for m in plan.milestones}
        known_milestones = {m.milestone_id for m in spec.milestones}
        for key, count in Counter(m.milestone_id for m in plan.milestones).items():
            if count > 1 or key not in known_milestones:
                issue("invalid_milestone", "里程碑重复或未在输入定义", f"milestone:{key}")
        for requirement in spec.milestones:
            ref = f"milestone:{requirement.milestone_id}"
            actual = milestones.get(requirement.milestone_id)
            if actual is None:
                issue("missing_milestone", "缺少必需里程碑", ref)
                continue
            if all(key in scheduled for key in requirement.work_ids):
                completed = max(scheduled[key].end_hour for key in requirement.work_ids)
                if actual.completion_hour != completed:
                    issue("milestone_completion", "里程碑完成时间必须与工作项一致", ref)
                if completed > requirement.deadline_hour:
                    issue("milestone_deadline", "里程碑超过期限", ref)
        return tuple(issues)
