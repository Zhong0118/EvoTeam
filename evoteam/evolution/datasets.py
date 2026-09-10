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

    def source_for(self, task: Task, *, partition: DatasetPartition) -> DatasetSource: ...


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

    def history_source_for(self, task: Task) -> DatasetSource | None:
        """Pin registered History at execution; ordinary online tasks remain allowed."""
        if any(
            entry.task_id == task.task_id
            for dataset in self.manifest.datasets
            if dataset.partition == DatasetPartition.HISTORY
            for entry in dataset.tasks
        ):
            return self.source_for(task, partition=DatasetPartition.HISTORY)
        return None


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
    """核对执行时封存的 History 来源，不用最新清单重写历史身份。"""

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
            source = sealed.dataset_source
            if source is None:
                raise ValueError("History 封存缺少执行时数据来源，不能追溯推断")
            if (
                snapshot.run.dataset_source != source
                or source.partition != DatasetPartition.HISTORY
                or source.task_id != sealed.task_id
                or source.task_fingerprint != task_fingerprint(snapshot.task)
                or snapshot.run.purpose != sealed.purpose
                or snapshot.run.strategy != sealed.strategy
            ):
                raise ValueError("History 数据来源与封存快照不一致")
            sources.append(source)
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

    def source_for(self, task: Task, *, partition: DatasetPartition) -> DatasetSource:
        if partition != DatasetPartition.VALIDATION:
            raise ValueError("旧 InMemoryValidationDatasets 只登记 Validation 数据")
        matches = [
            AssetRef(id=key[0], version=key[1])
            for key, tasks in self._datasets.items()
            if any(item.task_id == task.task_id for item in tasks)
        ]
        if len(matches) != 1:
            raise ValueError("InMemory Task 必须唯一登记")
        return DatasetSource(
            manifest_ref=AssetRef(id="in-memory", version="1"),
            dataset_ref=matches[0],
            partition=partition,
            task_id=task.task_id,
            task_fingerprint=task_fingerprint(task),
            subclass=task.task_type.value,
        )
