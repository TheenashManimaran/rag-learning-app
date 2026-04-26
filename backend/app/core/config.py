from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    app_name: str = "RAG Adaptive Learning App"
    api_prefix: str = "/api"
    database_path: Path = DATA_DIR / "learning.db"
    upload_dir: Path = DATA_DIR / "uploads"
    chroma_dir: Path = DATA_DIR / "indexes"
    gemini_api_key: str | None = None
    gemini_generation_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768
    max_upload_mb: int = 30
    top_k: int = 5
    chunk_size: int = 1200
    chunk_overlap: int = 180
    code_timeout_seconds: int = 5

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        env_prefix="",
        extra="ignore",
    )


settings = Settings()

settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
