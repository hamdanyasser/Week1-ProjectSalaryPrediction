from __future__ import annotations

from pathlib import Path

from config import Settings
from ml import FEATURE_COLUMNS, clean_salary_data, load_raw_data, train_and_save_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_test_settings(tmp_path: Path) -> Settings:
    return Settings(
        base_dir=tmp_path,
        app_env="test",
        log_level="INFO",
        dataset_path=PROJECT_ROOT / "data/raw/ds_salaries.csv",
        processed_data_path=tmp_path / "data/processed/cleaned_salaries.csv",
        model_path=tmp_path / "artifacts/decision_tree_pipeline.joblib",
        metrics_path=tmp_path / "artifacts/model_metrics.json",
        fastapi_host="127.0.0.1",
        fastapi_port=8000,
        fastapi_base_url="http://127.0.0.1:8000",
        streamlit_host="127.0.0.1",
        streamlit_port=8501,
        request_timeout_seconds=5,
    )


def test_clean_salary_data_preserves_expected_features() -> None:
    raw_df = load_raw_data(PROJECT_ROOT / "data/raw/ds_salaries.csv")
    cleaned_df = clean_salary_data(raw_df)

    assert not cleaned_df.empty
    assert all(column in cleaned_df.columns for column in FEATURE_COLUMNS)
    assert cleaned_df["salary_in_usd"].min() > 0


def test_train_and_save_model_creates_artifacts(tmp_path: Path) -> None:
    settings = build_test_settings(tmp_path)
    results = train_and_save_model(settings)

    assert settings.processed_data_path.exists()
    assert settings.model_path.exists()
    assert settings.metrics_path.exists()
    assert results["metrics"]["mae"] > 0

