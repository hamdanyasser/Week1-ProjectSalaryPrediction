from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


def _load_streamlit_secrets() -> None:
    """On Streamlit Cloud, secrets live in st.secrets, not env vars. Sync them."""
    try:
        from streamlit import secrets
        for key, value in secrets.items():
            if isinstance(value, str) and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    app_env: str
    log_level: str
    dataset_path: Path
    processed_data_path: Path
    model_path: Path
    metrics_path: Path
    fastapi_host: str
    fastapi_port: int
    fastapi_base_url: str
    streamlit_host: str
    streamlit_port: int
    request_timeout_seconds: int
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_timeout_seconds: int = 60
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_predictions_table: Optional[str] = None

    @property
    def ollama_enabled(self) -> bool:
        return bool(self.ollama_base_url and self.ollama_model)

    @property
    def supabase_write_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_predictions_table and self.supabase_service_role_key)

    @property
    def supabase_read_enabled(self) -> bool:
        return bool(
            self.supabase_url
            and self.supabase_predictions_table
            and (self.supabase_anon_key or self.supabase_service_role_key)
        )


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def _get_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


def _get_optional(name: str) -> Optional[str]:
    value = os.getenv(name, "").strip()
    return value or None


def load_settings(base_dir: Path | None = None) -> Settings:
    resolved_base_dir = (base_dir or BASE_DIR).resolve()
    load_dotenv(resolved_base_dir / ".env", override=False)
    _load_streamlit_secrets()
    fastapi_host = os.getenv("FASTAPI_HOST", "127.0.0.1")
    fastapi_port = _get_int("FASTAPI_PORT", 8000)

    return Settings(
        base_dir=resolved_base_dir,
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        dataset_path=_resolve_path(
            resolved_base_dir,
            os.getenv("DATASET_PATH", "data/raw/ds_salaries.csv"),
        ),
        processed_data_path=_resolve_path(
            resolved_base_dir,
            os.getenv("PROCESSED_DATA_PATH", "data/processed/cleaned_salaries.csv"),
        ),
        model_path=_resolve_path(
            resolved_base_dir,
            os.getenv("MODEL_PATH", "artifacts/decision_tree_pipeline.joblib"),
        ),
        metrics_path=_resolve_path(
            resolved_base_dir,
            os.getenv("METRICS_PATH", "artifacts/model_metrics.json"),
        ),
        fastapi_host=fastapi_host,
        fastapi_port=fastapi_port,
        fastapi_base_url=os.getenv("FASTAPI_BASE_URL", f"http://{fastapi_host}:{fastapi_port}"),
        streamlit_host=os.getenv("STREAMLIT_HOST", "127.0.0.1"),
        streamlit_port=_get_int("STREAMLIT_PORT", 8501),
        request_timeout_seconds=_get_int("REQUEST_TIMEOUT_SECONDS", 90),
        ollama_base_url=_get_optional("OLLAMA_BASE_URL"),
        ollama_model=_get_optional("OLLAMA_MODEL"),
        ollama_timeout_seconds=_get_int("OLLAMA_TIMEOUT_SECONDS", 60),
        supabase_url=_get_optional("SUPABASE_URL"),
        supabase_anon_key=_get_optional("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_get_optional("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_predictions_table=_get_optional("SUPABASE_PREDICTIONS_TABLE"),
    )


def ensure_runtime_directories(settings: Settings) -> None:
    settings.processed_data_path.parent.mkdir(parents=True, exist_ok=True)
    settings.model_path.parent.mkdir(parents=True, exist_ok=True)
    settings.metrics_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = load_settings()
    ensure_runtime_directories(settings)
    return settings
