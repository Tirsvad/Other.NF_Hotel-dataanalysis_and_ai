from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/nf_hotel_api/core/config.py -> project root is three levels up.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Central application configuration, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- API security ---
    api_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]

    # --- Local data source (fallback / default dataset) ---
    default_data_path: Path = Path("data/nf_hotel_bookings.csv")
    csv_separator: str = ";"
    # Reference data: room types, standard prices and how many rooms exist.
    metadata_path: Path = Path("data/hotel_metadata.json")

    @field_validator("default_data_path", "metadata_path")
    @classmethod
    def _resolve_relative_to_project_root(cls, value: Path) -> Path:
        # Anchored to the project root, not the process's current working
        # directory - otherwise this 404s whenever uvicorn/pytest is
        # launched from anywhere other than the repo root.
        return value if value.is_absolute() else _PROJECT_ROOT / value

    # --- LLM (OpenAI-compatible local inference server, e.g. vLLM / LM Studio) ---
    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen3.8-whittle-moe-27b-a17.8b"
    # Reasoning models can spend minutes generating <think>/reasoning_content
    # tokens before the final answer - keep this generous.
    llm_timeout_seconds: float = 900.0


@lru_cache
def get_settings() -> Settings:
    # api_key (and other required fields) come from the environment / .env
    # at runtime via BaseSettings, not from constructor arguments - static
    # type checkers can't see that, hence the ignore.
    return Settings()  # type: ignore[call-arg]
