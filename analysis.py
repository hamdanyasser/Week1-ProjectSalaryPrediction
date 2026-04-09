from __future__ import annotations

from typing import Any

import pandas as pd

from config import Settings
from ml import (
    TARGET_COLUMN,
    clean_salary_data,
    humanize_company_size,
    humanize_employment_type,
    humanize_experience_level,
    humanize_remote_ratio,
    load_raw_data,
)


def load_dashboard_data(settings: Settings) -> pd.DataFrame:
    if settings.processed_data_path.exists():
        return pd.read_csv(settings.processed_data_path)

    raw_df = load_raw_data(settings.dataset_path)
    cleaned_df = clean_salary_data(raw_df)
    settings.processed_data_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(settings.processed_data_path, index=False)
    return cleaned_df


def get_filter_options(df: pd.DataFrame) -> dict[str, list[Any]]:
    return {
        "experience_level": sorted(df["experience_level"].dropna().unique().tolist()),
        "employment_type": sorted(df["employment_type"].dropna().unique().tolist()),
        "job_title": sorted(df["job_title"].dropna().unique().tolist()),
        "employee_residence": sorted(df["employee_residence"].dropna().unique().tolist()),
        "company_location": sorted(df["company_location"].dropna().unique().tolist()),
        "company_size": sorted(df["company_size"].dropna().unique().tolist()),
        "remote_ratio": sorted(df["remote_ratio"].dropna().astype(int).unique().tolist()),
    }


def get_kpi_snapshot(df: pd.DataFrame) -> list[dict[str, str]]:
    median_salary = int(df[TARGET_COLUMN].median())
    highest_experience = (
        df.groupby("experience_level")[TARGET_COLUMN]
        .median()
        .sort_values(ascending=False)
        .index[0]
    )
    remote_leader = (
        df.groupby("remote_ratio")[TARGET_COLUMN]
        .median()
        .sort_values(ascending=False)
        .index[0]
    )

    return [
        {"label": "Records analyzed", "value": f"{len(df):,}"},
        {"label": "Median salary", "value": f"${median_salary:,.0f}"},
        {"label": "Top-paying experience level", "value": humanize_experience_level(highest_experience)},
        {"label": "Best-paid work style", "value": humanize_remote_ratio(int(remote_leader))},
    ]


def get_salary_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return df[[TARGET_COLUMN]].copy()


def get_experience_salary_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("experience_level")[TARGET_COLUMN]
        .agg(["median", "mean", "count"])
        .reset_index()
        .sort_values("median", ascending=False)
    )
    summary["experience_label"] = summary["experience_level"].map(humanize_experience_level)
    return summary


def get_employment_salary_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("employment_type")[TARGET_COLUMN]
        .agg(["median", "mean", "count"])
        .reset_index()
        .sort_values("median", ascending=False)
    )
    summary["employment_label"] = summary["employment_type"].map(humanize_employment_type)
    return summary


def get_remote_salary_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("remote_ratio")[TARGET_COLUMN]
        .agg(["median", "mean", "count"])
        .reset_index()
        .sort_values("median", ascending=False)
    )
    summary["remote_label"] = summary["remote_ratio"].map(humanize_remote_ratio)
    return summary


def get_top_roles_by_salary(df: pd.DataFrame, min_samples: int = 8, top_n: int = 8) -> pd.DataFrame:
    return (
        df.groupby("job_title")[TARGET_COLUMN]
        .agg(["median", "count"])
        .query("count >= @min_samples")
        .reset_index()
        .sort_values("median", ascending=False)
        .head(top_n)
    )


def get_role_spread_data(df: pd.DataFrame, min_samples: int = 8, top_n: int = 6) -> pd.DataFrame:
    spread = (
        df.groupby("job_title")[TARGET_COLUMN]
        .agg(["count", "std"])
        .query("count >= @min_samples")
        .sort_values("std", ascending=False)
        .head(top_n)
        .index.tolist()
    )
    return df[df["job_title"].isin(spread)].copy()


def build_takeaways(df: pd.DataFrame) -> list[str]:
    experience_summary = get_experience_salary_summary(df)
    role_summary = get_top_roles_by_salary(df)
    remote_summary = get_remote_salary_summary(df)

    top_experience = experience_summary.iloc[0]
    top_remote = remote_summary.iloc[0]
    takeaways = [
        f"{top_experience['experience_label']} roles have the highest median pay in this dataset.",
        f"{top_remote['remote_label']} roles lead the work-style comparison on median salary.",
    ]

    if not role_summary.empty:
        top_role = role_summary.iloc[0]
        takeaways.append(
            f"{top_role['job_title']} is one of the strongest-paying roles among titles with enough data points."
        )

    return takeaways[:3]


def _format_currency(value: float) -> str:
    return f"${value:,.0f}"


def _build_driver_messages(df: pd.DataFrame, payload: dict[str, Any]) -> list[str]:
    messages: list[str] = []

    role_group = df[df["job_title"] == payload["job_title"]]
    if len(role_group) >= 3:
        role_median = role_group[TARGET_COLUMN].median()
        messages.append(
            f"{payload['job_title']} roles in this dataset center around {_format_currency(role_median)}."
        )

    experience_group = df[df["experience_level"] == payload["experience_level"]]
    if len(experience_group) >= 3:
        exp_median = experience_group[TARGET_COLUMN].median()
        overall_median = df[TARGET_COLUMN].median()
        level_label = humanize_experience_level(payload["experience_level"])
        if exp_median >= overall_median:
            messages.append(f"{level_label} positions tend to earn above the market median in this dataset.")
        else:
            messages.append(f"{level_label} positions tend to earn below the market median, with room to grow at higher levels.")

    employment_group = df[df["employment_type"] == payload["employment_type"]]
    if len(employment_group) >= 3:
        employment_median = employment_group[TARGET_COLUMN].median()
        messages.append(
            f"{humanize_employment_type(payload['employment_type'])} roles have a median of {_format_currency(employment_median)} in this market snapshot."
        )

    remote_group = df[df["remote_ratio"] == payload["remote_ratio"]]
    if len(remote_group) >= 3:
        remote_median = remote_group[TARGET_COLUMN].median()
        messages.append(
            f"{humanize_remote_ratio(payload['remote_ratio'])} roles sit around {_format_currency(remote_median)} on median pay."
        )

    company_group = df[df["company_size"] == payload["company_size"]]
    if len(company_group) >= 3:
        company_median = company_group[TARGET_COLUMN].median()
        messages.append(
            f"{humanize_company_size(payload['company_size'])} companies in this dataset typically pay around {_format_currency(company_median)}."
        )

    return messages[:3]


def build_peer_context(df: pd.DataFrame, payload: dict[str, Any], predicted_salary: float) -> dict[str, Any]:
    matching_steps = [
        (
            "same role, experience level, employment type, and company size",
            (df["job_title"] == payload["job_title"])
            & (df["experience_level"] == payload["experience_level"])
            & (df["employment_type"] == payload["employment_type"])
            & (df["company_size"] == payload["company_size"]),
        ),
        (
            "same role, experience level, and employment type",
            (df["job_title"] == payload["job_title"])
            & (df["experience_level"] == payload["experience_level"])
            & (df["employment_type"] == payload["employment_type"]),
        ),
        (
            "same role and experience level",
            (df["job_title"] == payload["job_title"])
            & (df["experience_level"] == payload["experience_level"]),
        ),
        ("same role", df["job_title"] == payload["job_title"]),
        ("same experience level", df["experience_level"] == payload["experience_level"]),
        ("the full market", pd.Series([True] * len(df))),
    ]

    peer_group = df
    match_label = "the full market"
    for label, mask in matching_steps:
        candidate = df[mask]
        if len(candidate) >= 3:
            peer_group = candidate
            match_label = label
            break

    peer_median = float(peer_group[TARGET_COLUMN].median())
    peer_min = float(peer_group[TARGET_COLUMN].min())
    peer_max = float(peer_group[TARGET_COLUMN].max())
    difference = round(predicted_salary - peer_median, 2)

    if difference >= 0:
        comparison_text = f"This estimate is {_format_currency(abs(difference))} above the peer median."
    else:
        comparison_text = f"This estimate is {_format_currency(abs(difference))} below the peer median."

    explanation_summary = (
        f"The prediction is based on {len(peer_group)} rows from {match_label}. "
        f"That group has a typical salary of {_format_currency(peer_median)}, "
        f"with observed salaries ranging from {_format_currency(peer_min)} to {_format_currency(peer_max)}. "
        f"{comparison_text}"
    )

    return {
        "match_label": match_label,
        "sample_size": int(len(peer_group)),
        "peer_median_salary_usd": round(peer_median, 2),
        "peer_min_salary_usd": round(peer_min, 2),
        "peer_max_salary_usd": round(peer_max, 2),
        "difference_from_peer_median_usd": difference,
        "comparison_text": comparison_text,
        "driver_messages": _build_driver_messages(df, payload),
        "explanation_summary": explanation_summary,
    }
