from __future__ import annotations

import json
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from analysis import (
    build_takeaways,
    get_employment_salary_summary,
    get_experience_salary_summary,
    get_filter_options,
    get_kpi_snapshot,
    get_remote_salary_summary,
    get_role_spread_data,
    get_salary_distribution,
    get_top_roles_by_salary,
    load_dashboard_data,
)
from config import get_settings
from ml import (
    TARGET_COLUMN,
    humanize_company_size,
    humanize_country_code,
    humanize_employment_type,
    humanize_experience_level,
    humanize_remote_ratio,
    load_metrics,
)


BG = "#08111F"
SURFACE = "#101C2F"
SURFACE_ALT = "#14243B"
PRIMARY = "#14B8A6"
PRIMARY_DIM = "#0F766E"
ACCENT = "#38BDF8"
ACCENT_SOFT = "#818CF8"
TEXT = "#E5EEF8"
MUTED = "#93A4B8"
BORDER = "rgba(148, 163, 184, 0.12)"
SUCCESS_BG = "rgba(20, 184, 166, 0.12)"
AI_BG = "linear-gradient(135deg, rgba(20, 184, 166, 0.12), rgba(56, 189, 248, 0.10))"

CHART_COLORS = [PRIMARY, ACCENT, ACCENT_SOFT, "#F59E0B", "#F97316", "#A3E635"]
CHART_FONT = {"family": "Segoe UI, Arial, sans-serif", "color": TEXT, "size": 13}
CHART_MARGIN = {"l": 40, "r": 20, "t": 30, "b": 40}

SESSION_DEFAULTS = {
    "prediction_payload": None,
    "prediction_error": None,
    "llm_payload": None,
    "llm_chart_data": None,
    "llm_error": None,
}


st.set_page_config(page_title="PayScope", layout="wide")


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(20,184,166,0.10), transparent 28%),
                    radial-gradient(circle at top right, rgba(56,189,248,0.08), transparent 24%),
                    {BG};
                color: {TEXT};
            }}
            .block-container {{
                max-width: 1200px;
                padding-top: 2rem;
                padding-bottom: 4rem;
            }}
            .hero {{
                background: linear-gradient(135deg, #08111F 0%, #10314C 55%, #08111F 100%);
                border: 1px solid rgba(20,184,166,0.18);
                border-radius: 24px;
                padding: 2.5rem 2.5rem 2rem;
                box-shadow: 0 24px 60px rgba(0,0,0,0.30);
                margin-bottom: 2rem;
            }}
            .hero-badge {{
                display: inline-block;
                background: rgba(20,184,166,0.14);
                color: {PRIMARY};
                border: 1px solid rgba(20,184,166,0.22);
                border-radius: 999px;
                padding: 0.35rem 0.85rem;
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 1rem;
            }}
            .hero h1 {{
                color: #F8FBFF;
                font-size: 2.45rem;
                font-weight: 800;
                line-height: 1.15;
                margin-bottom: 0.55rem;
            }}
            .hero p {{
                color: {MUTED};
                font-size: 1.02rem;
                line-height: 1.7;
                max-width: 720px;
                margin: 0;
            }}
            .eyebrow {{
                color: {PRIMARY};
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.10em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }}
            .section-title {{
                color: #F8FBFF;
                font-size: 1.5rem;
                font-weight: 750;
                margin-bottom: 0.15rem;
            }}
            .section-subtitle {{
                color: {MUTED};
                font-size: 0.95rem;
                margin-bottom: 1.1rem;
            }}
            .metric-card {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 16px;
                padding: 1.1rem 1.15rem;
                min-height: 104px;
            }}
            .metric-label {{
                color: {MUTED};
                font-size: 0.82rem;
                margin-bottom: 0.4rem;
            }}
            .metric-value {{
                color: #F8FBFF;
                font-size: 1.46rem;
                font-weight: 760;
                line-height: 1.25;
            }}
            .chart-card {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 20px;
                padding: 1.2rem 1.2rem 0.8rem;
                margin-bottom: 1.2rem;
            }}
            .chart-title {{
                color: #F8FBFF;
                font-size: 1.08rem;
                font-weight: 700;
                margin-bottom: 0.2rem;
            }}
            .chart-subtitle {{
                color: {MUTED};
                font-size: 0.88rem;
                margin-bottom: 0.8rem;
            }}
            .chart-caption {{
                color: {MUTED};
                font-size: 0.88rem;
                margin-top: 0.45rem;
                margin-bottom: 0.35rem;
            }}
            .insight-box {{
                background: {SUCCESS_BG};
                border-left: 3px solid {PRIMARY};
                border-radius: 12px;
                padding: 0.95rem 1.05rem;
                color: {TEXT};
                font-size: 0.95rem;
                margin: 0.8rem 0 1.2rem;
            }}
            .prediction-shell {{
                background: linear-gradient(180deg, {SURFACE} 0%, {SURFACE_ALT} 100%);
                border: 1px solid rgba(20,184,166,0.18);
                border-radius: 20px;
                padding: 1.2rem;
            }}
            .result-card {{
                background: linear-gradient(160deg, #0B1324 0%, #11223A 100%);
                border: 1px solid rgba(20,184,166,0.20);
                border-radius: 20px;
                padding: 1.35rem;
                min-height: 240px;
                box-shadow: 0 18px 30px rgba(0,0,0,0.22);
            }}
            .result-label {{
                color: {MUTED};
                font-size: 0.86rem;
                margin-bottom: 0.3rem;
            }}
            .result-value {{
                color: {PRIMARY};
                font-size: 2.15rem;
                font-weight: 800;
                margin-bottom: 0.85rem;
            }}
            .driver-card {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
                padding: 1rem;
                height: 100%;
            }}
            .driver-title {{
                color: #F8FBFF;
                font-size: 0.98rem;
                font-weight: 700;
                margin-bottom: 0.65rem;
            }}
            .driver-line {{
                color: {TEXT};
                font-size: 0.9rem;
                line-height: 1.55;
                margin-bottom: 0.45rem;
            }}
            .ai-card {{
                background: {AI_BG};
                border: 1px solid rgba(20,184,166,0.20);
                border-radius: 18px;
                padding: 1.1rem 1.15rem;
                min-height: 100%;
            }}
            .ai-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                background: rgba(20,184,166,0.14);
                color: {PRIMARY};
                border: 1px solid rgba(20,184,166,0.24);
                border-radius: 999px;
                padding: 0.28rem 0.75rem;
                font-size: 0.74rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.8rem;
            }}
            .ai-dot {{
                width: 8px;
                height: 8px;
                border-radius: 999px;
                background: {PRIMARY};
                display: inline-block;
            }}
            .ai-headline {{
                color: #F8FBFF;
                font-size: 1rem;
                font-weight: 700;
                margin-bottom: 0.55rem;
            }}
            .ai-text {{
                color: {TEXT};
                font-size: 0.93rem;
                line-height: 1.65;
                margin-bottom: 0.75rem;
            }}
            .ai-list {{
                color: {MUTED};
                font-size: 0.88rem;
                line-height: 1.55;
                padding-left: 1rem;
                margin: 0;
            }}
            .takeaway-card {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 16px;
                padding: 1.05rem;
                min-height: 120px;
            }}
            .takeaway-index {{
                color: {PRIMARY};
                font-size: 0.8rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: 0.5rem;
            }}
            .footer {{
                color: {MUTED};
                font-size: 0.82rem;
                text-align: center;
                padding-top: 1.5rem;
                margin-top: 2.8rem;
                border-top: 1px solid {BORDER};
            }}
            .stButton > button {{
                background: {PRIMARY} !important;
                color: #08111F !important;
                font-weight: 700 !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 0.65rem 1.25rem !important;
            }}
            .stButton > button:hover {{
                background: {PRIMARY_DIM} !important;
                color: #E5EEF8 !important;
            }}
            div[data-testid="stForm"] {{
                border: none !important;
            }}
            .stSelectbox label {{
                color: {MUTED} !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_cached_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    settings = get_settings()
    return load_dashboard_data(settings), load_metrics(settings.metrics_path)


def initialize_session_state() -> None:
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, default_value)


def section_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='eyebrow'>{eyebrow}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def render_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_chart_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=CHART_FONT,
        margin=CHART_MARGIN,
        xaxis=dict(gridcolor="rgba(148,163,184,0.10)", zerolinecolor="rgba(148,163,184,0.10)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.10)", zerolinecolor="rgba(148,163,184,0.10)"),
    )
    return fig


def render_chart_card(title: str, subtitle: str) -> None:
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def close_chart_card() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def call_prediction_api(form_payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    settings = get_settings()
    try:
        response = requests.get(
            f"{settings.fastapi_base_url.rstrip('/')}/predict",
            params=form_payload,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "The API is not reachable yet. Start FastAPI to enable live predictions."
    except requests.exceptions.Timeout:
        return None, "The API took too long to respond. Please try again."
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        return None, f"Prediction request failed: {detail}"
    except ValueError:
        return None, "The API returned an unreadable response."


def build_llm_chart_data(prediction_payload: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    peer = prediction_payload["peer_context"]
    market_median = float(df[TARGET_COLUMN].median())
    return {
        "labels": ["Predicted salary", "Peer group median", "Market median"],
        "values": [
            round(float(prediction_payload["predicted_salary_usd"]), 2),
            round(float(peer["peer_median_salary_usd"]), 2),
            round(market_median, 2),
        ],
    }


def extract_json_object(raw_text: str) -> dict[str, Any] | None:
    start_index = raw_text.find("{")
    end_index = raw_text.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return None

    candidate = raw_text[start_index : end_index + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def generate_llm_analysis(
    prediction_payload: dict[str, Any],
    df: pd.DataFrame,
) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    settings = get_settings()
    chart_data = build_llm_chart_data(prediction_payload, df)

    if not settings.ollama_enabled:
        return None, chart_data, None

    peer = prediction_payload["peer_context"]
    predicted_salary = float(prediction_payload["predicted_salary_usd"])
    median_salary = float(df[TARGET_COLUMN].median())
    experience_summary = get_experience_salary_summary(df)
    top_roles = get_top_roles_by_salary(df, top_n=1)

    market_summary = {
        "records": int(len(df)),
        "median_salary_usd": round(median_salary, 2),
        "top_experience_level": experience_summary.iloc[0]["experience_label"],
        "top_role": top_roles.iloc[0]["job_title"] if not top_roles.empty else "Needs verification",
    }

    prompt = (
        "You are helping present a salary prediction to a non-technical audience. "
        "Return valid JSON only with this exact shape:\n"
        '{'
        '"headline": "short title", '
        '"narrative": "2 to 3 short sentences in plain English", '
        '"insights": ["short point", "short point"]'
        '}\n\n'
        f"Predicted salary: ${predicted_salary:,.0f}\n"
        f"Peer group label: {peer['match_label']}\n"
        f"Peer group sample size: {peer['sample_size']}\n"
        f"Peer group median salary: ${peer['peer_median_salary_usd']:,.0f}\n"
        f"Peer group range: ${peer['peer_min_salary_usd']:,.0f} to ${peer['peer_max_salary_usd']:,.0f}\n"
        f"Comparison: {peer['comparison_text']}\n"
        f"Market records: {market_summary['records']}\n"
        f"Market median salary: ${market_summary['median_salary_usd']:,.0f}\n"
        f"Top-paying experience level: {market_summary['top_experience_level']}\n"
        f"Top role by median salary: {market_summary['top_role']}\n"
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
        return None, chart_data, "Ollama is configured but not reachable right now."
    except ValueError:
        return None, chart_data, "Ollama returned an unreadable response."

    parsed_payload = extract_json_object(raw_text)
    if parsed_payload:
        headline = str(parsed_payload.get("headline", "AI salary summary")).strip() or "AI salary summary"
        narrative = str(parsed_payload.get("narrative", "")).strip() or raw_text
        insights = parsed_payload.get("insights", [])
        if not isinstance(insights, list):
            insights = []
        clean_insights = [str(item).strip() for item in insights if str(item).strip()][:2]
        return {
            "headline": headline,
            "narrative": narrative,
            "insights": clean_insights,
        }, chart_data, None

    return {
        "headline": "AI salary summary",
        "narrative": raw_text,
        "insights": [],
    }, chart_data, None


def load_supabase_history(limit: int = 20) -> tuple[pd.DataFrame | None, str | None]:
    settings = get_settings()
    if not settings.supabase_read_enabled:
        return None, None

    api_key = settings.supabase_anon_key or settings.supabase_service_role_key
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
    }
    params = {
        "select": "created_at,job_title,experience_level,employment_type,company_size,remote_ratio,predicted_salary_usd,comparison_text",
        "order": "created_at.desc",
        "limit": str(limit),
    }

    try:
        response = requests.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.supabase_predictions_table}",
            headers=headers,
            params=params,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        rows = response.json()
    except requests.RequestException:
        return None, "Supabase is configured but the saved history is not reachable yet."
    except ValueError:
        return None, "Supabase returned an unreadable response."

    if not rows:
        return pd.DataFrame(), None
    return pd.DataFrame(rows), None


def render_driver_card(driver_messages: list[str]) -> None:
    st.markdown("<div class='driver-card'>", unsafe_allow_html=True)
    st.markdown("<div class='driver-title'>What influenced this estimate?</div>", unsafe_allow_html=True)
    for message in driver_messages:
        st.markdown(f"<div class='driver-line'>- {message}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_ai_card(settings: Any, llm_payload: dict[str, Any] | None, llm_error: str | None) -> None:
    if llm_payload:
        insights_html = ""
        if llm_payload.get("insights"):
            bullets = "".join(f"<li>{item}</li>" for item in llm_payload["insights"])
            insights_html = f"<ul class='ai-list'>{bullets}</ul>"

        st.markdown(
            f"""
            <div class="ai-card">
                <div class="ai-badge"><span class="ai-dot"></span>AI Insight | {settings.ollama_model}</div>
                <div class="ai-headline">{llm_payload['headline']}</div>
                <div class="ai-text">{llm_payload['narrative']}</div>
                {insights_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if llm_error:
        st.info(llm_error)
    elif not settings.ollama_enabled:
        st.info("AI insight is off. Set OLLAMA_BASE_URL and OLLAMA_MODEL in .env to enable the local LLM.")
    else:
        st.info("Run a prediction to generate an AI explanation.")


def main() -> None:
    inject_css()
    initialize_session_state()

    settings = get_settings()
    df, metrics = load_cached_data()
    options = get_filter_options(df)

    st.markdown(
        """
        <div class="hero">
            <div class="hero-badge">PayScope</div>
            <h1>Understand the salary story before you trust the prediction.</h1>
            <p>
                PayScope turns salary data into a clear market story, then connects that story to one
                live prediction you can explain with confidence in front of a non-technical audience.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_header(
        "Market Snapshot",
        "A quick view of the salary landscape",
        "These headline numbers frame the market before we move into the strongest salary patterns.",
    )
    kpis = get_kpi_snapshot(df)
    kpi_columns = st.columns(len(kpis))
    for column, metric in zip(kpi_columns, kpis):
        with column:
            render_metric_card(metric["label"], metric["value"])

    if metrics:
        st.markdown(
            (
                f"<div class='insight-box'>The prediction model scores R\u00b2 "
                f"<strong>{metrics.get('r2', 'N/A')}</strong> and RMSE "
                f"<strong>${metrics.get('rmse', 0):,.0f}</strong> on held-out test data. "
                f"Higher R\u00b2 means better fit; lower RMSE means smaller average error.</div>"
            ),
            unsafe_allow_html=True,
        )

    section_header(
        "Distribution",
        "What does the overall salary market look like?",
        "Start with the big picture: where most salaries cluster and how wide the market can stretch.",
    )
    render_chart_card(
        "Salary distribution",
        "This shows the overall shape of the market before we break it down by role and experience.",
    )
    histogram = px.histogram(
        get_salary_distribution(df),
        x=TARGET_COLUMN,
        nbins=30,
        color_discrete_sequence=[PRIMARY],
    )
    histogram.update_layout(xaxis_title="Salary (USD)", yaxis_title="Number of records")
    st.plotly_chart(apply_chart_style(histogram), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        "<div class='chart-caption'>Most salaries sit in a central band, with a smaller set of roles stretching the upper end of the market.</div>",
        unsafe_allow_html=True,
    )
    close_chart_card()

    section_header(
        "Experience and Pay",
        "How does experience affect salary?",
        "Experience is one of the clearest patterns in the dataset, so it deserves an early spotlight.",
    )
    render_chart_card(
        "Experience level vs salary",
        "The box plot shows both the typical salary and how much variation exists inside each experience level.",
    )
    experience_plot_df = df.copy()
    experience_order = ["EN", "MI", "SE", "EX"]
    experience_plot_df["experience_label"] = experience_plot_df["experience_level"].map(humanize_experience_level)
    experience_chart = px.box(
        experience_plot_df,
        x="experience_label",
        y=TARGET_COLUMN,
        category_orders={"experience_label": [humanize_experience_level(code) for code in experience_order]},
        color_discrete_sequence=[PRIMARY],
        points=False,
    )
    experience_chart.update_layout(xaxis_title="", yaxis_title="Salary (USD)")
    st.plotly_chart(apply_chart_style(experience_chart), use_container_width=True, config={"displayModeBar": False})
    top_experience_label = get_experience_salary_summary(df).iloc[0]["experience_label"]
    st.markdown(
        f"<div class='chart-caption'>{top_experience_label} roles lead this comparison, which makes experience a strong signal in the prediction.</div>",
        unsafe_allow_html=True,
    )
    close_chart_card()

    section_header(
        "Employment Setup",
        "Which employment setup tends to pay more?",
        "This comparison keeps the story practical by linking salary to the kind of work arrangement a person has.",
    )
    render_chart_card(
        "Median salary by employment type",
        "Median salary keeps the comparison fair by reducing the effect of a few extreme outliers.",
    )
    employment_summary = get_employment_salary_summary(df)
    employment_chart = px.bar(
        employment_summary,
        x="employment_label",
        y="median",
        color="employment_label",
        color_discrete_sequence=CHART_COLORS,
    )
    employment_chart.update_layout(showlegend=False, xaxis_title="", yaxis_title="Median salary (USD)")
    st.plotly_chart(apply_chart_style(employment_chart), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        "<div class='chart-caption'>Employment type changes the pay story, so it deserves a place in the prediction input form.</div>",
        unsafe_allow_html=True,
    )
    close_chart_card()

    section_header(
        "Work Style",
        "Does remote, hybrid, or on-site pay differently?",
        "Work arrangement is one of the inputs to the prediction, so this chart shows how much it matters.",
    )
    render_chart_card(
        "Median salary by work style",
        "On-site, hybrid, and fully remote roles compared side by side on median pay.",
    )
    remote_summary = get_remote_salary_summary(df)
    remote_chart = px.bar(
        remote_summary,
        x="remote_label",
        y="median",
        color="remote_label",
        color_discrete_sequence=CHART_COLORS,
    )
    remote_chart.update_layout(showlegend=False, xaxis_title="", yaxis_title="Median salary (USD)")
    st.plotly_chart(apply_chart_style(remote_chart), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        "<div class='chart-caption'>Work style affects pay, but the gap depends on role and experience. The model uses this alongside other inputs.</div>",
        unsafe_allow_html=True,
    )
    close_chart_card()

    section_header(
        "Top Roles",
        "Which job titles tend to earn more?",
        "This turns the salary story into something recognizable by comparing well-known job titles.",
    )
    render_chart_card(
        "Top roles by median salary",
        "Only roles with enough examples are included so the ranking stays presentation-safe.",
    )
    top_roles = get_top_roles_by_salary(df)
    top_roles_chart = px.bar(
        top_roles.sort_values("median"),
        x="median",
        y="job_title",
        orientation="h",
        color_discrete_sequence=[PRIMARY],
    )
    top_roles_chart.update_layout(xaxis_title="Median salary (USD)", yaxis_title="")
    st.plotly_chart(apply_chart_style(top_roles_chart), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        "<div class='chart-caption'>Role title matters. Some jobs sit noticeably higher than others before we even add company or experience context.</div>",
        unsafe_allow_html=True,
    )
    close_chart_card()

    section_header(
        "Salary Spread",
        "Which roles show the widest salary spread?",
        "This is the chart that proves title alone is not enough to explain salary.",
    )
    render_chart_card(
        "Salary spread for the most variable roles",
        "The wider the spread, the more the model needs experience, company size, and work style to narrow the estimate.",
    )
    spread_df = get_role_spread_data(df)
    spread_chart = px.box(
        spread_df,
        x=TARGET_COLUMN,
        y="job_title",
        color="job_title",
        color_discrete_sequence=CHART_COLORS,
        points=False,
    )
    spread_chart.update_layout(showlegend=False, xaxis_title="Salary (USD)", yaxis_title="")
    st.plotly_chart(apply_chart_style(spread_chart), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        "<div class='chart-caption'>Some roles cover a wide pay range, which is why the prediction uses multiple inputs instead of title alone.</div>",
        unsafe_allow_html=True,
    )
    close_chart_card()

    section_header(
        "Prediction Studio",
        "Get a live salary estimate",
        "Choose a profile below and the model will predict an annual salary in USD based on the patterns in this dataset.",
    )
    left_column, right_column = st.columns([1.1, 0.9], gap="large")

    with left_column:
        st.markdown("<div class='prediction-shell'>", unsafe_allow_html=True)
        with st.form("prediction_form"):
            experience_level = st.selectbox(
                "Experience level",
                options=options["experience_level"],
                format_func=humanize_experience_level,
            )
            employment_type = st.selectbox(
                "Employment type",
                options=options["employment_type"],
                format_func=humanize_employment_type,
            )
            default_job_title = options["job_title"].index("Data Scientist") if "Data Scientist" in options["job_title"] else 0
            job_title = st.selectbox("Job title", options=options["job_title"], index=default_job_title)
            default_residence = options["employee_residence"].index("US") if "US" in options["employee_residence"] else 0
            employee_residence = st.selectbox(
                "Employee residence",
                options=options["employee_residence"],
                format_func=humanize_country_code,
                index=default_residence,
            )
            default_location = options["company_location"].index("US") if "US" in options["company_location"] else 0
            company_location = st.selectbox(
                "Company location",
                options=options["company_location"],
                format_func=humanize_country_code,
                index=default_location,
            )
            company_size = st.selectbox(
                "Company size",
                options=options["company_size"],
                format_func=humanize_company_size,
            )
            remote_ratio = st.selectbox(
                "Work style",
                options=options["remote_ratio"],
                format_func=humanize_remote_ratio,
            )
            submitted = st.form_submit_button("Predict salary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        payload = {
            "experience_level": experience_level,
            "employment_type": employment_type,
            "job_title": job_title,
            "employee_residence": employee_residence,
            "company_location": company_location,
            "company_size": company_size,
            "remote_ratio": remote_ratio,
        }
        prediction_payload, error_message = call_prediction_api(payload)
        if error_message:
            st.session_state["prediction_payload"] = None
            st.session_state["prediction_error"] = error_message
            st.session_state["llm_payload"] = None
            st.session_state["llm_chart_data"] = None
            st.session_state["llm_error"] = None
        else:
            llm_payload, llm_chart_data, llm_error = generate_llm_analysis(prediction_payload, df)
            st.session_state["prediction_payload"] = prediction_payload
            st.session_state["prediction_error"] = None
            st.session_state["llm_payload"] = llm_payload
            st.session_state["llm_chart_data"] = llm_chart_data
            st.session_state["llm_error"] = llm_error

    with right_column:
        prediction_payload = st.session_state["prediction_payload"]
        prediction_error = st.session_state["prediction_error"]
        if prediction_payload:
            predicted_salary = prediction_payload["predicted_salary_usd"]
            peer_context = prediction_payload["peer_context"]
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">Predicted annual salary (USD)</div>
                    <div class="result-value">${predicted_salary:,.0f}<span style="font-size:0.85rem;font-weight:500;color:{MUTED};margin-left:0.4rem">/ year</span></div>
                    <div style="color:{MUTED};font-size:0.92rem;margin-bottom:0.75rem">
                        Built from {peer_context['sample_size']} similar records in the dataset.
                    </div>
                    <div style="color:{TEXT};font-size:0.95rem;line-height:1.6">
                        {peer_context['comparison_text']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif prediction_error:
            st.warning(prediction_error)
        else:
            st.info("Start the API, submit the form, and the live prediction will appear here.")

    section_header(
        "Why This Prediction Makes Sense",
        "The data behind the estimate",
        "See how the prediction connects to real salary records, peer benchmarks, and market context.",
    )
    prediction_payload = st.session_state["prediction_payload"]
    if prediction_payload:
        peer_context = prediction_payload["peer_context"]
        summary_columns = st.columns(3)
        with summary_columns[0]:
            render_metric_card("Peer group", peer_context["match_label"].title())
        with summary_columns[1]:
            render_metric_card("Typical salary", f"${peer_context['peer_median_salary_usd']:,.0f}")
        with summary_columns[2]:
            render_metric_card(
                "Observed range",
                f"${peer_context['peer_min_salary_usd']:,.0f} - ${peer_context['peer_max_salary_usd']:,.0f}",
            )

        st.markdown(
            f"<div class='insight-box'>{peer_context['explanation_summary']}</div>",
            unsafe_allow_html=True,
        )

        detail_columns = st.columns([1.05, 0.95], gap="large")
        with detail_columns[0]:
            render_driver_card(peer_context["driver_messages"])

        with detail_columns[1]:
            llm_chart_data = st.session_state["llm_chart_data"]
            if llm_chart_data:
                render_chart_card(
                    "How the estimate compares",
                    "This chart compares the prediction against the peer group median and the broader market median.",
                )
                comparison_fig = go.Figure(
                    go.Bar(
                        x=llm_chart_data["values"],
                        y=llm_chart_data["labels"],
                        orientation="h",
                        marker_color=[PRIMARY, ACCENT, ACCENT_SOFT],
                        text=[f"${value:,.0f}" for value in llm_chart_data["values"]],
                        textposition="auto",
                    )
                )
                comparison_fig.update_layout(xaxis_title="Salary (USD)", yaxis_title="", height=260)
                st.plotly_chart(
                    apply_chart_style(comparison_fig),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
                st.markdown(
                    "<div class='chart-caption'>This is the supporting AI comparison chart: one clear view of the estimate against peer and market benchmarks.</div>",
                    unsafe_allow_html=True,
                )
                close_chart_card()

            render_ai_card(settings, st.session_state["llm_payload"], st.session_state["llm_error"])
    else:
        st.info("Run a prediction first, then this section will explain the result in plain English.")

    history_df, history_error = load_supabase_history()
    if history_df is not None or history_error:
        section_header(
            "History",
            "Saved predictions from Supabase",
            "Every prediction made through the API is persisted to Supabase. The dashboard reads directly from there.",
        )
        if history_error:
            st.info(history_error)
        elif history_df is not None and history_df.empty:
            st.info("Supabase is connected, but there are no saved predictions yet.")
        elif history_df is not None:
            display_df = history_df.rename(columns={
                "created_at": "Date",
                "job_title": "Role",
                "experience_level": "Experience",
                "employment_type": "Employment",
                "company_size": "Company size",
                "remote_ratio": "Work style",
                "predicted_salary_usd": "Predicted salary (USD)",
                "comparison_text": "Comparison",
            })
            if "Experience" in display_df.columns:
                display_df["Experience"] = display_df["Experience"].map(humanize_experience_level)
            if "Employment" in display_df.columns:
                display_df["Employment"] = display_df["Employment"].map(humanize_employment_type)
            if "Company size" in display_df.columns:
                display_df["Company size"] = display_df["Company size"].map(humanize_company_size)
            if "Work style" in display_df.columns:
                display_df["Work style"] = display_df["Work style"].apply(
                    lambda v: humanize_remote_ratio(int(v)) if pd.notna(v) else v
                )
            if "Date" in display_df.columns:
                display_df["Date"] = pd.to_datetime(display_df["Date"], errors="coerce").dt.strftime("%b %d, %Y %H:%M")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    section_header(
        "Takeaways",
        "Three insights the audience should remember",
        "These are short, presentation-ready points to close the story cleanly.",
    )
    takeaways = build_takeaways(df)
    takeaway_columns = st.columns(len(takeaways))
    for index, (column, takeaway) in enumerate(zip(takeaway_columns, takeaways), start=1):
        with column:
            st.markdown(
                f"""
                <div class="takeaway-card">
                    <div class="takeaway-index">Takeaway {index}</div>
                    <div style="color:{TEXT};font-size:0.93rem;line-height:1.55">{takeaway}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="footer">
            <strong>PayScope</strong> | Salary Prediction Dashboard | Yasser Hamdan
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
