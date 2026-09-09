"""框架无关的模型登记配置；凭据不进入 Strategy 或封存快照。"""

from typing import Annotated, Self

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator

from evoteam.domain.common import AssetRef, FrozenModel, Identifier, PositiveFloat, PositiveInt


class ModelEndpoint(FrozenModel):
    ref: AssetRef
    model_name: Identifier
    base_url: AnyHttpUrl
    api_key: SecretStr = Field(repr=False, exclude=True)
    timeout_seconds: PositiveFloat
    max_output_tokens: PositiveInt
    temperature: Annotated[float, Field(ge=0, le=2, allow_inf_nan=False)]
    top_p: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def reject_url_credentials(self) -> Self:
        if (
            self.base_url.username
            or self.base_url.password
            or self.base_url.query
            or self.base_url.fragment
        ):
            raise ValueError("模型地址不能包含凭据、查询参数或片段；密钥必须单独配置")
        return self
