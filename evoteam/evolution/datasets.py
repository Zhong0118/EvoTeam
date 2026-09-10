"""按版本化清单读取隔离数据；候选生成器无法访问这里。"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from evoteam.domain.common import AssetRef
from evoteam.domain.dataset import (
    DatasetManifest,
    DatasetPartition,
    DatasetSource,
    task_fingerprint,
)
from evoteam.domain.run import RunPurpose, SealedRun
from evoteam.domain.task import Task
from evoteam.storage.protocol import RunStore


class ValidationDatasetProvider(Protocol):
    def load(
        self, ref: AssetRef, *, partition: DatasetPartition = DatasetPartition.VALIDATION
    ) -> tuple[Task, ...]: ...


class HistoryEvidenceValidator(Protocol):
    async def validate(self, evidence: Sequence[SealedRun]) -> tuple[DatasetSource, ...]: ...


class ManifestDatasets:
    """清单校验在构造时完成；读取只返回防修改副本。"""

    def __init__(self, manifest: DatasetManifest) -> None:
        self.manifest = manifest
        self._by_ref = {
            (dataset.ref.id, dataset.ref.version): dataset for dataset in manifest.datasets
        }

    def _dataset(self, ref: AssetRef):
        try:
            return self._by_ref[(ref.id, ref.version)]
        except KeyError as error:
            raise ValueError(f"数据集 {ref.id}@{ref.version} 未登记") from error

    def load(
        self, ref: AssetRef, *, partition: DatasetPartition = DatasetPartition.VALIDATION
    ) -> tuple[Task, ...]:
        dataset = self._dataset(ref)
        if dataset.partition != partition:
            raise ValueError(
                f"{ref.id}@{ref.version} 属于 {dataset.partition.value}，"
                f"不能作为 {partition.value} 使用"
            )
        return tuple(entry.task.model_copy(deep=True) for entry in dataset.tasks)

    def source_for(self, task: Task, *, partition: DatasetPartition) -> DatasetSource:
        matches = [dataset for dataset in self.manifest.datasets if dataset.partition == partition]
        for dataset in matches:
            by_id = {entry.task_id: entry for entry in dataset.tasks}
            entry = by_id.get(task.task_id)
            if entry is None:
                continue
            if task_fingerprint(task) != entry.task_fingerprint:
                raise ValueError(f"{partition.value.title()} Task 内容摘要与登记清单不一致")
            return DatasetSource(
                manifest_ref=self.manifest.ref,
                dataset_ref=dataset.ref,
                partition=partition,
                task_id=entry.task_id,
                task_fingerprint=entry.task_fingerprint,
                subclass=entry.subclass,
            )
        raise ValueError(f"{partition.value.title()} Task ID 未在版本化清单登记")


class PackagedValidationDatasets(ManifestDatasets):
    """仓库默认项目规划清单；保留旧类名作为兼容入口。"""

    DEFAULT_MANIFEST = (
        Path(__file__).parents[2] / "examples" / "datasets" / "project_planning_manifest.json"
    )

    def __init__(self) -> None:
        super().__init__(
            DatasetManifest.model_validate_json(self.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        )


class ManifestHistoryValidator:
    """只读取 History 注册和封存快照，不读取 Validation/Final Test 任务。"""

    def __init__(self, datasets: ManifestDatasets, runs: RunStore) -> None:
        self.datasets = datasets
        self.runs = runs

    async def validate(self, evidence: Sequence[SealedRun]) -> tuple[DatasetSource, ...]:
        sources = []
        for sealed in evidence:
            if sealed.purpose != RunPurpose.ONLINE:
                raise ValueError("History 证据必须来自 online Run")
            snapshot = await self.runs.read_snapshot(sealed.run_id)
            if (
                snapshot.task.task_id != sealed.task_id
                or snapshot.run.run_id != sealed.run_id
                or snapshot.run.task_id != sealed.task_id
            ):
                raise ValueError("History Run 与封存 TaskSnapshot 身份不匹配")
            sources.append(
                self.datasets.source_for(snapshot.task, partition=DatasetPartition.HISTORY)
            )
        return tuple(sources)


class InMemoryValidationDatasets:
    """测试和受控实验使用；复制输入以防候选修改验证数据。"""

    def __init__(self, datasets: Mapping[tuple[str, str], Sequence[Task]]) -> None:
        self._datasets = {
            key: tuple(task.model_copy(deep=True) for task in value)
            for key, value in datasets.items()
        }

    def load(
        self, ref: AssetRef, *, partition: DatasetPartition = DatasetPartition.VALIDATION
    ) -> tuple[Task, ...]:
        if partition != DatasetPartition.VALIDATION:
            raise ValueError("旧 InMemoryValidationDatasets 只登记 Validation 数据")
        tasks = self._datasets[(ref.id, ref.version)]
        return tuple(task.model_copy(deep=True) for task in tasks)
