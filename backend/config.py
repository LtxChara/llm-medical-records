import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    api_key: str = Field(alias="siliconflow_api_key")
    base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        alias="siliconflow_base_url"
    )
    llm_model_name: str = Field(
        default="Qwen/Qwen3.5-4B",
        alias="llm_model_name"
    )
    llm_timeout: float = Field(default=30.0, alias="llm_timeout")
    llm_max_retries: int = Field(default=2, alias="llm_max_retries")
    session_ttl_seconds: int = Field(default=3600, alias="session_ttl_seconds")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )


settings = Settings()
