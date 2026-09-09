"""解析版本化项目规划输入；不选择团队、不生成策略。"""

from evoteam.domain.planning import parse_planning_task
from evoteam.domain.task import Task, TaskProfile


class TaskAnalyzer:
    def analyze(self, task: Task) -> TaskProfile:
        spec = parse_planning_task(task)
        return TaskProfile(
            task_id=task.task_id,
            task_type=task.task_type,
            constraint_refs=(
                "deadline_hour",
                "budget_minor",
                *(m.milestone_id for m in spec.milestones),
            ),
        )
