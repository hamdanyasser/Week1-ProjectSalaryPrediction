from __future__ import annotations

import json
import logging
from enum import Enum
from functools import lru_cache
from typing import Annotated, Any

import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from analysis import (
    build_peer_context,
    get_experience_salary_summary,
    get_top_roles_by_salary,
    load_dashboard_data,
)
from config import Settings, get_settings
from ml import TARGET_COLUMN, load_model_bundle, normalize_prediction_inputs, predict_salary


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


class LlmAnalysisResponse(BaseModel):
    headline: str
    narrative: str
    insights: list[str] = []
    model: str | None = None


class PredictionResponse(BaseModel):
    predicted_salary_usd: float = Field(..., description="Predicted salary in USD.")
    normalized_inputs: dict[str, Any]
    model_name: str
    peer_context: PeerContextResponse
    llm_analysis: LlmAnalysisResponse | None = None


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


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def generate_llm_analysis(
    settings: Settings,
    predicted_salary: float,
    peer_context: dict[str, Any],
    dashboard_df: Any,
) -> dict[str, Any] | None:
    if not settings.ollama_enabled:
        return None

    median_salary = float(dashboard_df[TARGET_COLUMN].median())
    experience_summary = get_experience_salary_summary(dashboard_df)
    top_roles = get_top_roles_by_salary(dashboard_df, top_n=1)

    prompt = (
        "You are helping present a salary prediction to a non-technical audience. "
        "Return valid JSON only with this exact shape:\n"
        '{"headline": "short title", '
        '"narrative": "2 to 3 short sentences in plain English", '
        '"insights": ["short point", "short point"]}\n\n'
        f"Predicted salary: ${predicted_salary:,.0f}\n"
        f"Peer group label: {peer_context['match_label']}\n"
        f"Peer group sample size: {peer_context['sample_size']}\n"
        f"Peer group median salary: ${peer_context['peer_median_salary_usd']:,.0f}\n"
        f"Peer group range: ${peer_context['peer_min_salary_usd']:,.0f} to ${peer_context['peer_max_salary_usd']:,.0f}\n"
        f"Comparison: {peer_context['comparison_text']}\n"
        f"Market records: {len(dashboard_df)}\n"
        f"Market median salary: ${median_salary:,.0f}\n"
        f"Top-paying experience level: {experience_summary.iloc[0]['experience_label']}\n"
        f"Top role by median salary: {top_roles.iloc[0]['job_title'] if not top_roles.empty else 'N/A'}\n"
        "Keep the response simple, concrete, and presentation-ready. Avoid jargon."
    )

    try:
        response = requests.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        raw_text = response.json().get("response", "").strip()
    except requests.RequestException:
        logger.warning("Ollama not reachable, skipping LLM analysis.")
        return None
    except ValueError:
        logger.warning("Ollama returned unreadable response.")
        return None

    parsed = _extract_json_object(raw_text)
    if parsed:
        headline = str(parsed.get("headline", "AI salary summary")).strip() or "AI salary summary"
        narrative = str(parsed.get("narrative", "")).strip() or raw_text
        insights = parsed.get("insights", [])
        if not isinstance(insights, list):
            insights = []
        clean_insights = [str(item).strip() for item in insights if str(item).strip()][:2]
        return {"headline": headline, "narrative": narrative, "insights": clean_insights, "model": settings.ollama_model}

    return {"headline": "AI salary summary", "narrative": raw_text, "insights": [], "model": settings.ollama_model}


def save_prediction_to_supabase(
    settings: Settings,
    payload: dict[str, Any],
    predicted_salary: float,
    peer_context: dict[str, Any],
    llm_result: dict[str, Any] | None = None,
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
    if llm_result:
        record["llm_headline"] = llm_result.get("headline", "")
        record["llm_narrative"] = llm_result.get("narrative", "")
        record["llm_insights"] = json.dumps(llm_result.get("insights", []))

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
        llm_result = generate_llm_analysis(app_settings, predicted_salary, peer_context, dashboard_df)
        save_prediction_to_supabase(app_settings, payload, predicted_salary, peer_context, llm_result)

        return PredictionResponse(
            predicted_salary_usd=predicted_salary,
            normalized_inputs=payload,
            model_name=model_bundle["metadata"]["model_name"],
            peer_context=PeerContextResponse(**peer_context),
            llm_analysis=LlmAnalysisResponse(**llm_result) if llm_result else None,
        )

    return app


app = create_app()
