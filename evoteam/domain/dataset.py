"""版本化实验数据清单与内容身份；不包含模型答案或候选生成逻辑。"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from evoteam.domain.common import AssetRef, FrozenModel, Identifier
from evoteam.domain.task import Task


class DatasetPartition(StrEnum):
    HISTORY = "history"
    VALIDATION = "validation"
    FINAL_TEST = "final_test"


def task_fingerprint(task: Task) -> str:
    """摘要结构化题目，排除可改名的 task_id 和可改写的 instruction。"""
    canonical = json.dumps(
        {
            "task_type": task.task_type.value,
            "input_schema": task.input_schema.model_dump(mode="json"),
            "inputs": task.inputs,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_partitions(partitions: Mapping[str, Sequence[Task]]) -> None:
    expected = {partition.value for partition in DatasetPartition}
    if set(partitions) != expected:
        raise ValueError("数据分区键必须且只能是 history、validation、final_test")
    task_ids: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    for partition in DatasetPartition:
        tasks = partitions[partition.value]
        if not tasks:
            raise ValueError(f"{partition.value} 分区不能为空")
        for task in tasks:
            previous_partition = task_ids.get(task.task_id)
            if previous_partition is not None:
                raise ValueError(
                    f"Task ID {task.task_id} 在 {previous_partition}/{partition.value} 重复"
                )
            task_ids[task.task_id] = partition.value
            fingerprint = task_fingerprint(task)
            previous_partition = fingerprints.get(fingerprint)
            if previous_partition is not None:
                if previous_partition != partition.value:
                    raise ValueError("同一结构化题目不能跨分区复用，即使修改 ID 或 instruction")
                raise ValueError(f"{partition.value} 分区包含重复内容")
            fingerprints[fingerprint] = partition.value


class DatasetTask(FrozenModel):
    task_id: Identifier
    task_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    subclass: Identifier
    human_review: Identifier
    task: Task

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        if self.task_id != self.task.task_id:
            raise ValueError("清单 task_id 与 Task 身份不一致")
        if self.task_fingerprint != task_fingerprint(self.task):
            raise ValueError("清单内容摘要与 Task 不一致；同引用内容可能已变更")
        return self


class PartitionDataset(FrozenModel):
    ref: AssetRef
    partition: DatasetPartition
    tasks: tuple[DatasetTask, ...] = Field(min_length=1)


class DatasetManifest(FrozenModel):
    ref: AssetRef
    datasets: tuple[PartitionDataset, ...] = Field(min_length=3)

    @model_validator(mode="after")
    def verify_partitions(self) -> Self:
        refs = tuple((dataset.ref.id, dataset.ref.version) for dataset in self.datasets)
        if len(set(refs)) != len(refs):
            raise ValueError("数据集 AssetRef 不能重复")
        partitions = tuple(dataset.partition for dataset in self.datasets)
        if len(set(partitions)) != len(partitions):
            raise ValueError("每种数据分区只能登记一次")
        validate_partitions(
            {
                dataset.partition.value: tuple(entry.task for entry in dataset.tasks)
                for dataset in self.datasets
            }
        )
        return self


class DatasetSource(FrozenModel):
    """执行前固定、随 Run 封存的版本化数据来源。"""

    manifest_ref: AssetRef
    dataset_ref: AssetRef
    partition: DatasetPartition
    task_id: Identifier
    task_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    subclass: Identifier
