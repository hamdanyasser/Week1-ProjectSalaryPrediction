from __future__ import annotations

import logging
from enum import Enum
from functools import lru_cache
from typing import Annotated, Any

import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from analysis import build_peer_context, load_dashboard_data
from config import Settings, get_settings
from ml import load_model_bundle, normalize_prediction_inputs, predict_salary


logger = logging.getLogger(__name__)


class ExperienceLevel(str, Enum):
    EN = "EN"
    MI = "MI"
    SE = "SE"
    EX = "EX"


class EmploymentType(str, Enum):
    FT = "FT"
    PT = "PT"
    CT = "CT"
    FL = "FL"


class CompanySize(str, Enum):
    S = "S"
    M = "M"
    L = "L"


class HealthResponse(BaseModel):
    status: str
    model_ready: bool
    data_ready: bool


class PeerContextResponse(BaseModel):
    match_label: str
    sample_size: int
    peer_median_salary_usd: float
    peer_min_salary_usd: float
    peer_max_salary_usd: float
    difference_from_peer_median_usd: float
    comparison_text: str
    driver_messages: list[str]
    explanation_summary: str


class PredictionResponse(BaseModel):
    predicted_salary_usd: float = Field(..., description="Predicted salary in USD.")
    normalized_inputs: dict[str, Any]
    model_name: str
    peer_context: PeerContextResponse


def get_runtime_bundle(settings: Settings) -> tuple[dict[str, Any], Any]:
    try:
        model_bundle = load_model_bundle(settings.model_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Model artifact is missing. Run train_model.py before requesting predictions.",
        ) from exc

    try:
        dashboard_df = load_dashboard_data(settings)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Dataset is missing. Confirm that data/raw/ds_salaries.csv exists.",
        ) from exc

    return model_bundle, dashboard_df


def save_prediction_to_supabase(
    settings: Settings,
    payload: dict[str, Any],
    predicted_salary: float,
    peer_context: dict[str, Any],
) -> None:
    if not settings.supabase_write_enabled:
        return

    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.supabase_predictions_table}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    record = {
        **payload,
        "predicted_salary_usd": predicted_salary,
        "peer_group_label": peer_context["match_label"],
        "peer_group_size": peer_context["sample_size"],
        "peer_median_salary_usd": peer_context["peer_median_salary_usd"],
        "peer_min_salary_usd": peer_context["peer_min_salary_usd"],
        "peer_max_salary_usd": peer_context["peer_max_salary_usd"],
        "comparison_text": peer_context["comparison_text"],
        "explanation_summary": peer_context["explanation_summary"],
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=record,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Supabase persistence failed: %s", exc)


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="PayScope API",
        description="Local salary prediction service for the PayScope dashboard.",
        version="1.0.0",
    )
    app_settings = settings or get_settings()

    @lru_cache(maxsize=1)
    def _cached_runtime_bundle() -> tuple[dict[str, Any], Any]:
        return get_runtime_bundle(app_settings)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            model_ready=app_settings.model_path.exists(),
            data_ready=app_settings.dataset_path.exists(),
        )

    @app.get("/predict", response_model=PredictionResponse)
    def predict(
        experience_level: ExperienceLevel,
        employment_type: EmploymentType,
        job_title: Annotated[str, Query(min_length=2, max_length=100)],
        employee_residence: Annotated[str, Query(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")],
        company_location: Annotated[str, Query(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")],
        company_size: CompanySize,
        remote_ratio: Annotated[int, Query(ge=0, le=100)],
    ) -> PredictionResponse:
        if remote_ratio not in {0, 50, 100}:
            raise HTTPException(
                status_code=422,
                detail="remote_ratio must be one of: 0, 50, 100.",
            )

        model_bundle, dashboard_df = _cached_runtime_bundle()

        payload = normalize_prediction_inputs(
            {
                "experience_level": experience_level.value,
                "employment_type": employment_type.value,
                "job_title": job_title,
                "employee_residence": employee_residence,
                "company_location": company_location,
                "company_size": company_size.value,
                "remote_ratio": remote_ratio,
            }
        )

        predicted_salary = predict_salary(model_bundle, payload)
        peer_context = build_peer_context(dashboard_df, payload, predicted_salary)
        save_prediction_to_supabase(app_settings, payload, predicted_salary, peer_context)

        return PredictionResponse(
            predicted_salary_usd=predicted_salary,
            normalized_inputs=payload,
            model_name=model_bundle["metadata"]["model_name"],
            peer_context=PeerContextResponse(**peer_context),
        )

    return app


app = create_app()
