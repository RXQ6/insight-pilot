from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql://insight:insight@localhost:5432/insight"
    postgres_readonly_dsn: str = ""
    sandbox_mode: str = "local"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    embedding_model: str = "BAAI/bge-m3"

    task_input_stream: str = "task:input"
    task_result_stream: str = "task:result"
    task_dlq_stream: str = "task:dlq"
    consumer_group: str = "agent-worker"

    max_steps: int = 8
    tool_loop_limit: int = 5
    max_tool_output_chars: int = 20_000
    sql_timeout_seconds: int = 10
    query_row_limit: int = 1_000
    llm_timeout_seconds: int = 60
    cost_cap_cny: float = 0.2
    sandbox_python: str = "python"


settings = Settings()
