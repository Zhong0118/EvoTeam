"""由开发者校准和冻结的参数；所有阈值必须显式提供。"""

from typing import Self

from pydantic import model_validator

from evoteam.domain.common import (
    AssetRef,
    FrozenModel,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    Probability,
)
from evoteam.domain.evolution import TriggerType


class EvolutionPolicy(FrozenModel):
    ref: AssetRef
    window_size: PositiveInt
    min_samples: PositiveInt
    repeated_failure_threshold: PositiveInt
    quality_drop_threshold: Probability
    cost_overrun_threshold: NonNegativeFloat
    low_contribution_threshold: NonNegativeFloat
    cooldown_runs: NonNegativeInt
    max_candidates: PositiveInt
    stable_window_count: PositiveInt
    enabled_triggers: tuple[TriggerType, ...] = (TriggerType.REPEATED_FAILURE,)

    @model_validator(mode="after")
    def validate_window_limits(self) -> Self:
        if (
            self.min_samples > self.window_size
            or self.repeated_failure_threshold > self.window_size
        ):
            raise ValueError("样本量与重复阈值不能超过窗口大小")
        return self
