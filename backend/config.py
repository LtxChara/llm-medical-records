import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    siliconflow_api_key: str
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    llm_model_name: str = "Qwen/Qwen3.5-4B"
    llm_timeout: float = 30.0
    llm_max_retries: int = 2
    session_ttl_seconds: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
