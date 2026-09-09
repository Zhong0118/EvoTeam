"""所有领域对象共用的类型；配置使用冻结模型和 tuple。"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(min_length=1)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]
PositiveFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class DomainModel(BaseModel):
    """拒绝未知字段，防止运行数据意外混入领域配置。"""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FrozenModel(DomainModel):
    """禁止字段赋值；嵌套集合仍应采用不可变类型。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AssetRef(FrozenModel):
    """固定版本的能力引用，不能使用 latest 表达可复现配置。"""

    id: Identifier
    version: Identifier


class StrategyRef(FrozenModel):
    strategy_id: Identifier
    version: NonNegativeInt


class RunBudget(FrozenModel):
    """None 表示尚未配置；真实执行前必须明确预算，不代表无限。"""

    max_tokens: PositiveInt | None = None
    max_tool_calls: NonNegativeInt | None = None
    timeout_seconds: PositiveFloat | None = None
