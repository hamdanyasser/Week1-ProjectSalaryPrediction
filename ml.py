from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

from config import Settings, ensure_runtime_directories


TARGET_COLUMN = "salary_in_usd"
FEATURE_COLUMNS = [
    "experience_level",
    "employment_type",
    "job_title",
    "employee_residence",
    "company_location",
    "company_size",
    "remote_ratio",
]
NUMERIC_FEATURES = ["remote_ratio"]
CATEGORICAL_FEATURES = [column for column in FEATURE_COLUMNS if column not in NUMERIC_FEATURES]

EXPERIENCE_LABELS = {
    "EN": "Entry level",
    "MI": "Mid level",
    "SE": "Senior level",
    "EX": "Executive level",
}
EMPLOYMENT_LABELS = {
    "FT": "Full time",
    "PT": "Part time",
    "CT": "Contract",
    "FL": "Freelance",
}
COMPANY_SIZE_LABELS = {
    "S": "Small company",
    "M": "Medium company",
    "L": "Large company",
}
REMOTE_RATIO_LABELS = {
    0: "On-site",
    50: "Hybrid",
    100: "Fully remote",
}
COUNTRY_NAMES: dict[str, str] = {
    "AE": "United Arab Emirates",
    "AR": "Argentina",
    "AS": "American Samoa",
    "AT": "Austria",
    "AU": "Australia",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BO": "Bolivia",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "DZ": "Algeria",
    "EE": "Estonia",
    "ES": "Spain",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "HK": "Hong Kong",
    "HN": "Honduras",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IQ": "Iraq",
    "IR": "Iran",
    "IT": "Italy",
    "JE": "Jersey",
    "JP": "Japan",
    "KE": "Kenya",
    "LU": "Luxembourg",
    "MD": "Moldova",
    "MT": "Malta",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NG": "Nigeria",
    "NL": "Netherlands",
    "NZ": "New Zealand",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PR": "Puerto Rico",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SG": "Singapore",
    "SI": "Slovenia",
    "TN": "Tunisia",
    "TR": "Turkey",
    "UA": "Ukraine",
    "US": "United States",
    "VN": "Vietnam",
}


def load_raw_data(dataset_path: Path) -> pd.DataFrame:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found at {dataset_path}")
    return pd.read_csv(dataset_path)


def clean_salary_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()

    if "Unnamed: 0" in cleaned.columns:
        cleaned = cleaned.drop(columns=["Unnamed: 0"])

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in cleaned.columns]
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    cleaned = cleaned[required_columns].dropna().copy()
    cleaned["job_title"] = cleaned["job_title"].astype(str).str.strip()
    cleaned["employee_residence"] = cleaned["employee_residence"].astype(str).str.strip().str.upper()
    cleaned["company_location"] = cleaned["company_location"].astype(str).str.strip().str.upper()
    cleaned["experience_level"] = cleaned["experience_level"].astype(str).str.strip().str.upper()
    cleaned["employment_type"] = cleaned["employment_type"].astype(str).str.strip().str.upper()
    cleaned["company_size"] = cleaned["company_size"].astype(str).str.strip().str.upper()
    cleaned["remote_ratio"] = pd.to_numeric(cleaned["remote_ratio"], errors="coerce")
    cleaned[TARGET_COLUMN] = pd.to_numeric(cleaned[TARGET_COLUMN], errors="coerce")

    cleaned = cleaned.dropna(
        subset=["job_title", "employee_residence", "company_location", "remote_ratio", TARGET_COLUMN]
    )
    cleaned = cleaned[cleaned["job_title"] != ""]
    cleaned = cleaned[cleaned["remote_ratio"].isin([0, 50, 100])]
    cleaned = cleaned[cleaned[TARGET_COLUMN] > 0]
    cleaned["remote_ratio"] = cleaned["remote_ratio"].astype(int)
    cleaned[TARGET_COLUMN] = cleaned[TARGET_COLUMN].astype(float)

    return cleaned.reset_index(drop=True)


def build_model_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "regressor",
                DecisionTreeRegressor(
                    max_depth=12,
                    min_samples_leaf=4,
                    random_state=42,
                ),
            ),
        ]
    )


def save_cleaned_data(cleaned_df: pd.DataFrame, settings: Settings) -> None:
    ensure_runtime_directories(settings)
    cleaned_df.to_csv(settings.processed_data_path, index=False)


def evaluate_model(pipeline: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    predictions = pipeline.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))

    return {
        "mae": round(float(mean_absolute_error(y_test, predictions)), 2),
        "rmse": round(rmse, 2),
        "r2": round(float(r2_score(y_test, predictions)), 4),
        "test_rows": int(len(X_test)),
    }


def train_and_save_model(settings: Settings) -> dict[str, Any]:
    ensure_runtime_directories(settings)
    raw_df = load_raw_data(settings.dataset_path)
    cleaned_df = clean_salary_data(raw_df)
    save_cleaned_data(cleaned_df, settings)

    X = cleaned_df[FEATURE_COLUMNS]
    y = cleaned_df[TARGET_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    pipeline = build_model_pipeline()
    pipeline.fit(X_train, y_train)
    metrics = evaluate_model(pipeline, X_test, y_test)

    model_bundle = {
        "pipeline": pipeline,
        "metadata": {
            "model_name": "DecisionTreeRegressor",
            "feature_columns": FEATURE_COLUMNS,
            "target_column": TARGET_COLUMN,
            "trained_at_utc": datetime.now(timezone.utc).isoformat(),
            "training_rows": int(len(X_train)),
            "total_rows": int(len(cleaned_df)),
        },
    }

    joblib.dump(model_bundle, settings.model_path)
    settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return {
        "metrics": metrics,
        "metadata": model_bundle["metadata"],
        "cleaned_rows": int(len(cleaned_df)),
    }


def load_model_bundle(model_path: Path) -> dict[str, Any]:
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at {model_path}")
    return joblib.load(model_path)


def load_metrics(metrics_path: Path) -> dict[str, Any]:
    if not metrics_path.exists():
        return {}
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def normalize_prediction_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "experience_level": str(payload["experience_level"]).strip().upper(),
        "employment_type": str(payload["employment_type"]).strip().upper(),
        "job_title": str(payload["job_title"]).strip(),
        "employee_residence": str(payload["employee_residence"]).strip().upper(),
        "company_location": str(payload["company_location"]).strip().upper(),
        "company_size": str(payload["company_size"]).strip().upper(),
        "remote_ratio": int(payload["remote_ratio"]),
    }


def build_prediction_frame(payload: dict[str, Any]) -> pd.DataFrame:
    normalized = normalize_prediction_inputs(payload)
    return pd.DataFrame([normalized], columns=FEATURE_COLUMNS)


def predict_salary(model_bundle: dict[str, Any], payload: dict[str, Any]) -> float:
    prediction_frame = build_prediction_frame(payload)
    pipeline = model_bundle["pipeline"]
    predicted_value = pipeline.predict(prediction_frame)[0]
    return round(float(predicted_value), 2)


def humanize_experience_level(code: str) -> str:
    return EXPERIENCE_LABELS.get(code, code)


def humanize_employment_type(code: str) -> str:
    return EMPLOYMENT_LABELS.get(code, code)


def humanize_company_size(code: str) -> str:
    return COMPANY_SIZE_LABELS.get(code, code)


def humanize_remote_ratio(value: int) -> str:
    return REMOTE_RATIO_LABELS.get(value, f"{value}% remote")


def humanize_country_code(code: str) -> str:
    return COUNTRY_NAMES.get(code, code)

