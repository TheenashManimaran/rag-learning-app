from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    app_name: str = "RAG Adaptive Learning App"
    api_prefix: str = "/api"
    database_path: Path = DATA_DIR / "learning.db"
    upload_dir: Path = DATA_DIR / "uploads"
    faiss_index_dir: Path = DATA_DIR / "faiss"
    gemini_api_key: str | None = None
    xai_api_key: str | None = None
    groq_api_key: str | None = None
    mistral_api_key: str | None = None
    librarian_model: str = "gemini/gemini-3-flash"
    orchestrator_model: str = "groq/llama-3.3-70b-versatile"
    judge_model: str = "mistral/open-mistral-nemo"
    gemini_generation_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768
    max_upload_mb: int = 30
    top_k: int = 5
    chunk_size: int = 1200
    chunk_overlap: int = 180
    code_timeout_seconds: int = 5

    @field_validator("database_path", "upload_dir", "faiss_index_dir", mode="after")
    @classmethod
    def resolve_local_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else PROJECT_ROOT / value

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
        case_sensitive=False
    )


settings = Settings()


def ensure_runtime_dirs() -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.faiss_index_dir.mkdir(parents=True, exist_ok=True)


ensure_runtime_dirs()
