from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api import create_app
from config import Settings
from ml import train_and_save_model


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


def test_predict_endpoint_returns_prediction(tmp_path: Path) -> None:
    settings = build_test_settings(tmp_path)
    train_and_save_model(settings)
    client = TestClient(create_app(settings))

    response = client.get(
        "/predict",
        params={
            "experience_level": "SE",
            "employment_type": "FT",
            "job_title": "Data Scientist",
            "employee_residence": "US",
            "company_location": "US",
            "company_size": "M",
            "remote_ratio": 100,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_salary_usd"] > 0
    assert "peer_context" in payload


def test_predict_endpoint_rejects_invalid_query(tmp_path: Path) -> None:
    settings = build_test_settings(tmp_path)
    train_and_save_model(settings)
    client = TestClient(create_app(settings))

    response = client.get(
        "/predict",
        params={
            "experience_level": "BAD",
            "employment_type": "FT",
            "job_title": "Data Scientist",
            "employee_residence": "USA",
            "company_location": "US",
            "company_size": "M",
            "remote_ratio": 101,
        },
    )

    assert response.status_code == 422
