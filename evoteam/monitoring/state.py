"""监控检查点，不改变 Strategy 生命周期；SQLite 使用 revision 原子比较。"""

from typing import Protocol

from evoteam.domain.common import FrozenModel, NonNegativeInt
from evoteam.domain.evolution import MonitorResult


class MonitorState(FrozenModel):
    revision: NonNegativeInt = 0
    policy_fingerprint: str | None = None
    seen_run_ids: tuple[str, ...] = ()
    last_trigger_sample_count: NonNegativeInt | None = None
    last_window_ids: tuple[str, ...] = ()
    last_result: MonitorResult | None = None


class MonitorStore(Protocol):
    async def load(self, key: str) -> MonitorState: ...
    async def save(self, key: str, *, expected_revision: int, state: MonitorState) -> None: ...
