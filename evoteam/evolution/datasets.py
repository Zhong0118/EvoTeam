"""只按登记引用读取验证任务，候选生成器无法访问这里。"""

import json
from collections.abc import Mapping, Sequence
from importlib.resources import files
from types import MappingProxyType
from typing import Protocol

from evoteam.domain.common import AssetRef
from evoteam.domain.task import Task


class ValidationDatasetProvider(Protocol):
    def load(self, ref: AssetRef) -> tuple[Task, ...]: ...


class PackagedValidationDatasets:
    DATASET_FILES: Mapping[tuple[str, str], str] = MappingProxyType(
        {("project-planning-validation", "1"): "project_planning_v1.json"}
    )

    def load(self, ref: AssetRef) -> tuple[Task, ...]:
        relative = self.DATASET_FILES[(ref.id, ref.version)]
        raw = json.loads(
            files("evoteam.validation_datasets").joinpath(relative).read_text(encoding="utf-8")
        )
        if not isinstance(raw, list) or not raw:
            raise ValueError("验证集必须是非空 Task 数组")
        tasks = tuple(Task.model_validate(item) for item in raw)
        if len({task.task_id for task in tasks}) != len(tasks):
            raise ValueError("验证集 Task ID 不能重复")
        return tasks


class InMemoryValidationDatasets:
    """测试和受控实验使用；复制输入以防候选修改验证数据。"""

    def __init__(self, datasets: Mapping[tuple[str, str], Sequence[Task]]) -> None:
        self._datasets = {
            key: tuple(task.model_copy(deep=True) for task in value)
            for key, value in datasets.items()
        }

    def load(self, ref: AssetRef) -> tuple[Task, ...]:
        tasks = self._datasets[(ref.id, ref.version)]
        return tuple(task.model_copy(deep=True) for task in tasks)
