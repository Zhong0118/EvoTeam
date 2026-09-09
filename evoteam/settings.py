"""显式加载环境；模型凭据不写入领域配置或错误输出。"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from evoteam.domain.common import AssetRef
from evoteam.runtime.models import ModelEndpoint


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVOTEAM_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///evoteam.db"
    model_id: str | None = None
    model_version: str | None = None
    model_name: str | None = None
    model_base_url: str | None = None
    model_api_key: SecretStr | None = None
    model_timeout_seconds: float | None = None
    model_max_output_tokens: int | None = None
    model_temperature: float | None = None
    model_top_p: float | None = None

    def runtime_model(self) -> ModelEndpoint:
        fields = (
            "model_id",
            "model_version",
            "model_name",
            "model_base_url",
            "model_api_key",
            "model_timeout_seconds",
            "model_max_output_tokens",
            "model_temperature",
            "model_top_p",
        )
        if any(getattr(self, name) is None for name in fields):
            raise ValueError("真实 Runtime 配置不完整，请填写 .env.example 中的模型字段")
        if not all(
            value and value.strip()
            for value in (self.model_id, self.model_version, self.model_name, self.model_base_url)
        ):
            raise ValueError("模型身份或地址配置为空")
        assert self.model_id and self.model_version and self.model_name and self.model_base_url
        assert self.model_api_key is not None
        if not self.model_api_key.get_secret_value().strip():
            raise ValueError("模型密钥配置为空")
        return ModelEndpoint.model_validate(
            {
                "ref": AssetRef(id=self.model_id, version=self.model_version),
                "model_name": self.model_name,
                "base_url": self.model_base_url,
                "api_key": self.model_api_key,
                "timeout_seconds": self.model_timeout_seconds,
                "max_output_tokens": self.model_max_output_tokens,
                "temperature": self.model_temperature,
                "top_p": self.model_top_p,
            }
        )
