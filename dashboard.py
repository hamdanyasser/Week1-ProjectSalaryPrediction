from __future__ import annotations

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


# ── colour system ────────────────────────────────────────────────────────
BG          = "#0A0E1A"
SURFACE     = "#12172B"
SURFACE_ALT = "#191F38"
CARD_GLASS  = "rgba(22, 28, 56, 0.65)"

TEAL        = "#00E5C3"
TEAL_DIM    = "#00B89C"
CORAL       = "#FF6B6B"
AMBER       = "#FFB547"
VIOLET      = "#A78BFA"
SKY         = "#38BDF8"
LIME        = "#84CC16"
PINK        = "#F472B6"

TEXT        = "#EDF2F7"
MUTED       = "#8B95A8"
BORDER      = "rgba(255,255,255,0.06)"

CHART_PALETTE = [TEAL, CORAL, AMBER, VIOLET, SKY, LIME, PINK]
CHART_FONT    = {"family": "'Inter', 'Segoe UI', system-ui, sans-serif", "color": TEXT, "size": 13}
CHART_MARGIN  = {"l": 48, "r": 24, "t": 36, "b": 44}

SESSION_DEFAULTS = {
    "prediction_payload": None,
    "prediction_error": None,
}


st.set_page_config(page_title="PayScope", layout="wide", page_icon="$")


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500&display=swap');

            :root {{
                --teal: {TEAL};
                --coral: {CORAL};
                --amber: {AMBER};
                --violet: {VIOLET};
            }}

            .stApp {{
                background:
                    radial-gradient(ellipse 80% 60% at 10% 0%, rgba(0,229,195,0.07), transparent),
                    radial-gradient(ellipse 70% 50% at 90% 10%, rgba(255,107,107,0.05), transparent),
                    radial-gradient(ellipse 60% 40% at 50% 90%, rgba(167,139,250,0.05), transparent),
                    {BG};
                color: {TEXT};
                font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            }}
            .block-container {{
                max-width: 1220px;
                padding-top: 1.5rem;
                padding-bottom: 4rem;
            }}

            /* ── hero ─────────────────────────────────────────────── */
            .hero {{
                position: relative;
                background: linear-gradient(135deg, #0D1127 0%, #141B3D 40%, #1A1040 70%, #0D1127 100%);
                border: 1px solid rgba(0,229,195,0.12);
                border-radius: 28px;
                padding: 3rem 2.8rem 2.5rem;
                margin-bottom: 2.2rem;
                overflow: hidden;
            }}
            .hero::before {{
                content: '';
                position: absolute;
                top: -40%;
                right: -10%;
                width: 420px;
                height: 420px;
                background: radial-gradient(circle, rgba(0,229,195,0.12), transparent 70%);
                border-radius: 50%;
                pointer-events: none;
            }}
            .hero::after {{
                content: '';
                position: absolute;
                bottom: -30%;
                left: 15%;
                width: 300px;
                height: 300px;
                background: radial-gradient(circle, rgba(255,107,107,0.08), transparent 70%);
                border-radius: 50%;
                pointer-events: none;
            }}
            .hero-tag {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background: rgba(0,229,195,0.10);
                color: {TEAL};
                border: 1px solid rgba(0,229,195,0.20);
                border-radius: 999px;
                padding: 0.38rem 1rem;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 1.2rem;
                position: relative;
            }}
            .hero-tag .dot {{
                width: 7px; height: 7px;
                border-radius: 50%;
                background: {TEAL};
                animation: pulse-dot 2s ease-in-out infinite;
            }}
            @keyframes pulse-dot {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.3; }}
            }}
            .hero h1 {{
                color: #FFFFFF;
                font-size: 2.6rem;
                font-weight: 900;
                line-height: 1.12;
                margin-bottom: 0.6rem;
                letter-spacing: -0.02em;
                position: relative;
            }}
            .hero h1 .highlight {{
                background: linear-gradient(135deg, {TEAL}, {SKY});
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .hero p {{
                color: {MUTED};
                font-size: 1.05rem;
                line-height: 1.75;
                max-width: 660px;
                margin: 0;
                position: relative;
            }}

            /* ── section headers ──────────────────────────────────── */
            .section-tag {{
                display: inline-block;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.13em;
                text-transform: uppercase;
                padding: 0.3rem 0.75rem;
                border-radius: 6px;
                margin-bottom: 0.5rem;
            }}
            .section-tag.teal   {{ background: rgba(0,229,195,0.10); color: {TEAL}; }}
            .section-tag.coral  {{ background: rgba(255,107,107,0.10); color: {CORAL}; }}
            .section-tag.amber  {{ background: rgba(255,181,71,0.10); color: {AMBER}; }}
            .section-tag.violet {{ background: rgba(167,139,250,0.10); color: {VIOLET}; }}
            .section-tag.sky    {{ background: rgba(56,189,248,0.10); color: {SKY}; }}
            .section-tag.lime   {{ background: rgba(132,204,22,0.10); color: {LIME}; }}
            .section-tag.pink   {{ background: rgba(244,114,182,0.10); color: {PINK}; }}
            .section-title {{
                color: #FFFFFF;
                font-size: 1.55rem;
                font-weight: 800;
                margin-bottom: 0.15rem;
                letter-spacing: -0.01em;
            }}
            .section-sub {{
                color: {MUTED};
                font-size: 0.93rem;
                margin-bottom: 1.15rem;
                line-height: 1.5;
            }}

            /* ── KPI metric cards ─────────────────────────────────── */
            .kpi {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 1.15rem 1.2rem;
                position: relative;
                overflow: hidden;
                min-height: 108px;
            }}
            .kpi::after {{
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 3px;
                border-radius: 18px 18px 0 0;
            }}
            .kpi.c0::after {{ background: linear-gradient(90deg, {TEAL}, {SKY}); }}
            .kpi.c1::after {{ background: linear-gradient(90deg, {AMBER}, {CORAL}); }}
            .kpi.c2::after {{ background: linear-gradient(90deg, {VIOLET}, {PINK}); }}
            .kpi.c3::after {{ background: linear-gradient(90deg, {SKY}, {TEAL}); }}
            .kpi-label {{
                color: {MUTED};
                font-size: 0.78rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: 0.45rem;
            }}
            .kpi-value {{
                color: #FFFFFF;
                font-size: 1.5rem;
                font-weight: 800;
                line-height: 1.2;
            }}

            /* ── chart cards ──────────────────────────────────────── */
            .chart-wrap {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 20px;
                padding: 1.3rem 1.3rem 0.9rem;
                margin-bottom: 1.2rem;
            }}
            .chart-head {{
                color: #FFFFFF;
                font-size: 1.05rem;
                font-weight: 700;
                margin-bottom: 0.15rem;
            }}
            .chart-desc {{
                color: {MUTED};
                font-size: 0.85rem;
                margin-bottom: 0.8rem;
            }}
            .chart-note {{
                color: {MUTED};
                font-size: 0.84rem;
                margin-top: 0.4rem;
                padding-top: 0.55rem;
                border-top: 1px solid {BORDER};
            }}

            /* ── insight callout ──────────────────────────────────── */
            .callout {{
                border-radius: 14px;
                padding: 1rem 1.15rem;
                font-size: 0.94rem;
                line-height: 1.65;
                color: {TEXT};
                margin: 0.8rem 0 1.2rem;
            }}
            .callout.teal {{
                background: rgba(0,229,195,0.08);
                border-left: 3px solid {TEAL};
            }}
            .callout.amber {{
                background: rgba(255,181,71,0.08);
                border-left: 3px solid {AMBER};
            }}
            .callout.violet {{
                background: rgba(167,139,250,0.08);
                border-left: 3px solid {VIOLET};
            }}

            /* ── prediction form shell ────────────────────────────── */
            .form-shell {{
                background: linear-gradient(180deg, {SURFACE} 0%, {SURFACE_ALT} 100%);
                border: 1px solid rgba(0,229,195,0.12);
                border-radius: 22px;
                padding: 1.3rem;
            }}

            /* ── result card (salary output) ──────────────────────── */
            .salary-result {{
                background: linear-gradient(145deg, #101530 0%, #161D40 50%, #1A1240 100%);
                border: 1px solid rgba(0,229,195,0.18);
                border-radius: 22px;
                padding: 1.5rem;
                min-height: 250px;
                position: relative;
                overflow: hidden;
            }}
            .salary-result::before {{
                content: '';
                position: absolute;
                top: -50%;
                right: -30%;
                width: 250px;
                height: 250px;
                background: radial-gradient(circle, rgba(0,229,195,0.10), transparent 70%);
                border-radius: 50%;
                pointer-events: none;
            }}
            .salary-result .label {{
                color: {MUTED};
                font-size: 0.84rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: 0.35rem;
                position: relative;
            }}
            .salary-result .amount {{
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 2.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, {TEAL}, {SKY});
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.3rem;
                position: relative;
            }}
            .salary-result .yr {{
                font-size: 0.9rem;
                font-weight: 500;
                color: {MUTED};
                -webkit-text-fill-color: {MUTED};
                background: none;
                -webkit-background-clip: unset;
                background-clip: unset;
            }}
            .salary-result .context {{
                color: {MUTED};
                font-size: 0.9rem;
                margin-bottom: 0.8rem;
                position: relative;
            }}
            .salary-result .comparison {{
                color: {TEXT};
                font-size: 0.95rem;
                line-height: 1.6;
                position: relative;
            }}

            /* ── driver card (explanation) ─────────────────────────── */
            .drivers {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 1.1rem;
            }}
            .drivers .head {{
                color: #FFFFFF;
                font-size: 0.98rem;
                font-weight: 700;
                margin-bottom: 0.7rem;
            }}
            .drivers .line {{
                display: flex;
                align-items: flex-start;
                gap: 0.55rem;
                margin-bottom: 0.55rem;
            }}
            .drivers .bullet {{
                flex-shrink: 0;
                width: 6px;
                height: 6px;
                border-radius: 50%;
                margin-top: 0.5rem;
            }}
            .drivers .line:nth-child(2) .bullet {{ background: {TEAL}; }}
            .drivers .line:nth-child(3) .bullet {{ background: {AMBER}; }}
            .drivers .line:nth-child(4) .bullet {{ background: {CORAL}; }}
            .drivers .line:nth-child(5) .bullet {{ background: {VIOLET}; }}
            .drivers .msg {{
                color: {TEXT};
                font-size: 0.9rem;
                line-height: 1.55;
            }}

            /* ── AI card ──────────────────────────────────────────── */
            .ai-card {{
                background: linear-gradient(135deg, rgba(0,229,195,0.07), rgba(167,139,250,0.06), rgba(56,189,248,0.05));
                border: 1px solid rgba(0,229,195,0.15);
                border-radius: 20px;
                padding: 1.2rem 1.25rem;
                min-height: 100%;
            }}
            .ai-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                background: rgba(0,229,195,0.12);
                color: {TEAL};
                border: 1px solid rgba(0,229,195,0.22);
                border-radius: 999px;
                padding: 0.25rem 0.7rem;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.85rem;
            }}
            .ai-badge .dot {{
                width: 7px; height: 7px;
                border-radius: 50%;
                background: {TEAL};
                animation: pulse-dot 2s ease-in-out infinite;
            }}
            .ai-headline {{
                color: #FFFFFF;
                font-size: 1.02rem;
                font-weight: 700;
                margin-bottom: 0.55rem;
            }}
            .ai-text {{
                color: {TEXT};
                font-size: 0.92rem;
                line-height: 1.7;
                margin-bottom: 0.8rem;
            }}
            .ai-list {{
                padding-left: 1.1rem;
                margin: 0;
            }}
            .ai-list li {{
                color: {MUTED};
                font-size: 0.87rem;
                line-height: 1.55;
                margin-bottom: 0.3rem;
            }}

            /* ── takeaway cards ────────────────────────────────────── */
            .takeaway {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 1.15rem;
                min-height: 130px;
                position: relative;
                overflow: hidden;
            }}
            .takeaway::after {{
                content: '';
                position: absolute;
                bottom: 0; left: 0; right: 0;
                height: 3px;
                border-radius: 0 0 18px 18px;
            }}
            .takeaway.t0::after {{ background: linear-gradient(90deg, {TEAL}, {SKY}); }}
            .takeaway.t1::after {{ background: linear-gradient(90deg, {CORAL}, {AMBER}); }}
            .takeaway.t2::after {{ background: linear-gradient(90deg, {VIOLET}, {PINK}); }}
            .takeaway .num {{
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                margin-bottom: 0.55rem;
            }}
            .takeaway.t0 .num {{ color: {TEAL}; }}
            .takeaway.t1 .num {{ color: {CORAL}; }}
            .takeaway.t2 .num {{ color: {VIOLET}; }}
            .takeaway .body {{
                color: {TEXT};
                font-size: 0.92rem;
                line-height: 1.55;
            }}

            /* ── footer ───────────────────────────────────────────── */
            .footer {{
                text-align: center;
                padding-top: 1.5rem;
                margin-top: 3rem;
                border-top: 1px solid {BORDER};
            }}
            .footer span {{
                color: {MUTED};
                font-size: 0.8rem;
            }}
            .footer .name {{
                color: {TEAL};
                font-weight: 700;
            }}

            /* ── streamlit overrides ──────────────────────────────── */
            .stButton > button {{
                background: linear-gradient(135deg, {TEAL}, {TEAL_DIM}) !important;
                color: #0A0E1A !important;
                font-weight: 700 !important;
                border: none !important;
                border-radius: 14px !important;
                padding: 0.7rem 1.3rem !important;
                font-size: 0.95rem !important;
                letter-spacing: 0.02em !important;
                transition: all 0.2s ease !important;
            }}
            .stButton > button:hover {{
                filter: brightness(1.15) !important;
                transform: translateY(-1px) !important;
                box-shadow: 0 8px 24px rgba(0,229,195,0.25) !important;
            }}
            div[data-testid="stForm"] {{
                border: none !important;
            }}
            .stSelectbox label, .stSlider label {{
                color: {MUTED} !important;
                font-weight: 500 !important;
                font-size: 0.85rem !important;
            }}
            .stDataFrame {{
                border-radius: 16px !important;
                overflow: hidden !important;
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


def section_header(tag: str, tag_color: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='section-tag {tag_color}'>{tag}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-sub'>{subtitle}</div>", unsafe_allow_html=True)


def render_kpi(label: str, value: str, index: int) -> None:
    st.markdown(
        f"""<div class="kpi c{index % 4}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def apply_chart_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=CHART_FONT,
        margin=CHART_MARGIN,
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)"),
    )
    return fig


def chart_open(title: str, desc: str) -> None:
    st.markdown("<div class='chart-wrap'>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-head'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-desc'>{desc}</div>", unsafe_allow_html=True)


def chart_note(text: str) -> None:
    st.markdown(f"<div class='chart-note'>{text}</div>", unsafe_allow_html=True)


def chart_close() -> None:
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


def render_drivers(driver_messages: list[str]) -> None:
    lines_html = ""
    for msg in driver_messages:
        lines_html += f'<div class="line"><span class="bullet"></span><span class="msg">{msg}</span></div>'
    st.markdown(
        f"""<div class="drivers">
            <div class="head">What influenced this estimate?</div>
            {lines_html}
        </div>""",
        unsafe_allow_html=True,
    )


def render_ai_card(llm_analysis: dict[str, Any] | None) -> None:
    if llm_analysis:
        model_label = llm_analysis.get("model") or "Local LLM"
        insights_html = ""
        if llm_analysis.get("insights"):
            bullets = "".join(f"<li>{item}</li>" for item in llm_analysis["insights"])
            insights_html = f"<ul class='ai-list'>{bullets}</ul>"

        st.markdown(
            f"""<div class="ai-card">
                <div class="ai-badge"><span class="dot"></span>AI Insight &middot; {model_label}</div>
                <div class="ai-headline">{llm_analysis['headline']}</div>
                <div class="ai-text">{llm_analysis['narrative']}</div>
                {insights_html}
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("AI narrative is generated when predictions run through the local pipeline with Ollama enabled.")


# ── main ─────────────────────────────────────────────────────────────────

def main() -> None:
    inject_css()
    initialize_session_state()

    settings = get_settings()
    df, metrics = load_cached_data()
    options = get_filter_options(df)

    # ── 1. Hero ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero">
            <div class="hero-tag"><span class="dot"></span> PayScope</div>
            <h1>Understand the <span class="highlight">salary story</span><br>before you trust the prediction.</h1>
            <p>
                PayScope turns salary data into a clear market story, then connects that story
                to one live prediction you can explain with confidence.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 2. KPI cards ─────────────────────────────────────────────────────
    section_header("Market Snapshot", "teal", "A quick view of the salary landscape",
                   "These headline numbers frame the market before we dig into the patterns.")
    kpis = get_kpi_snapshot(df)
    kpi_cols = st.columns(len(kpis))
    for i, (col, metric) in enumerate(zip(kpi_cols, kpis)):
        with col:
            render_kpi(metric["label"], metric["value"], i)

    if metrics:
        st.markdown(
            f"""<div class="callout teal">
                The prediction model scores R\u00b2 <strong>{metrics.get('r2', 'N/A')}</strong>
                and RMSE <strong>${metrics.get('rmse', 0):,.0f}</strong> on held-out test data.
                Higher R\u00b2 = better fit. Lower RMSE = smaller average error.
            </div>""",
            unsafe_allow_html=True,
        )

    # ── 3. Salary distribution ───────────────────────────────────────────
    section_header("Distribution", "coral", "What does the overall salary market look like?",
                   "Start with the big picture: where most salaries cluster and how wide the market stretches.")
    chart_open("Salary distribution", "The overall shape of the market before we break it down by role and experience.")
    hist = px.histogram(
        get_salary_distribution(df), x=TARGET_COLUMN, nbins=30,
        color_discrete_sequence=[TEAL],
    )
    hist.update_layout(xaxis_title="Salary (USD)", yaxis_title="Records")
    st.plotly_chart(apply_chart_style(hist), use_container_width=True, config={"displayModeBar": False})
    chart_note("Most salaries sit in a central band, with a smaller set of roles stretching the upper end.")
    chart_close()

    # ── 4. Experience ────────────────────────────────────────────────────
    section_header("Experience & Pay", "amber", "How does experience affect salary?",
                   "Experience is one of the clearest patterns in the dataset.")

    exp_df = df.copy()
    exp_order = ["EN", "MI", "SE", "EX"]
    exp_df["experience_label"] = exp_df["experience_level"].map(humanize_experience_level)
    chart_open("Experience level vs salary", "The box plot shows the typical salary and variation inside each level.")
    exp_chart = px.box(
        exp_df, x="experience_label", y=TARGET_COLUMN,
        category_orders={"experience_label": [humanize_experience_level(c) for c in exp_order]},
        color="experience_label",
        color_discrete_sequence=[TEAL, AMBER, CORAL, VIOLET],
        points=False,
    )
    exp_chart.update_layout(showlegend=False, xaxis_title="", yaxis_title="Salary (USD)")
    st.plotly_chart(apply_chart_style(exp_chart), use_container_width=True, config={"displayModeBar": False})
    top_exp = get_experience_salary_summary(df).iloc[0]["experience_label"]
    chart_note(f"{top_exp} roles lead this comparison \u2014 experience is a strong signal in the prediction.")
    chart_close()

    # ── 5. Employment type ───────────────────────────────────────────────
    section_header("Employment Setup", "violet", "Which employment setup tends to pay more?",
                   "Linking salary to the kind of work arrangement a person has.")
    chart_open("Median salary by employment type", "Median keeps the comparison fair by reducing outlier effects.")
    emp_summary = get_employment_salary_summary(df)
    emp_chart = px.bar(
        emp_summary, x="employment_label", y="median",
        color="employment_label", color_discrete_sequence=CHART_PALETTE,
    )
    emp_chart.update_layout(showlegend=False, xaxis_title="", yaxis_title="Median salary (USD)")
    st.plotly_chart(apply_chart_style(emp_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Employment type changes the pay story \u2014 it deserves a place in the prediction input.")
    chart_close()

    # ── 6. Work style ────────────────────────────────────────────────────
    section_header("Work Style", "sky", "Does remote, hybrid, or on-site pay differently?",
                   "Work arrangement is one of the prediction inputs \u2014 this chart shows how much it matters.")
    chart_open("Median salary by work style", "On-site, hybrid, and fully remote compared side by side.")
    remote_summary = get_remote_salary_summary(df)
    remote_chart = px.bar(
        remote_summary, x="remote_label", y="median",
        color="remote_label", color_discrete_sequence=[CORAL, AMBER, TEAL],
    )
    remote_chart.update_layout(showlegend=False, xaxis_title="", yaxis_title="Median salary (USD)")
    st.plotly_chart(apply_chart_style(remote_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Work style affects pay, but the gap depends on role and experience. The model uses all inputs together.")
    chart_close()

    # ── 7. Top roles ─────────────────────────────────────────────────────
    section_header("Top Roles", "lime", "Which job titles tend to earn more?",
                   "Comparing well-known titles so the salary story feels recognizable.")
    chart_open("Top roles by median salary", "Only roles with enough data points are included.")
    top_roles = get_top_roles_by_salary(df)
    roles_chart = px.bar(
        top_roles.sort_values("median"), x="median", y="job_title", orientation="h",
        color_discrete_sequence=[TEAL],
    )
    roles_chart.update_layout(xaxis_title="Median salary (USD)", yaxis_title="")
    st.plotly_chart(apply_chart_style(roles_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Role title matters \u2014 some jobs sit noticeably higher before we add company or experience context.")
    chart_close()

    # ── 8. Salary spread ─────────────────────────────────────────────────
    section_header("Salary Spread", "pink", "Which roles show the widest salary range?",
                   "This proves title alone is not enough to explain salary.")
    chart_open("Salary spread for the most variable roles",
               "The wider the spread, the more the model needs other inputs to narrow the estimate.")
    spread_df = get_role_spread_data(df)
    spread_chart = px.box(
        spread_df, x=TARGET_COLUMN, y="job_title",
        color="job_title", color_discrete_sequence=CHART_PALETTE, points=False,
    )
    spread_chart.update_layout(showlegend=False, xaxis_title="Salary (USD)", yaxis_title="")
    st.plotly_chart(apply_chart_style(spread_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Wide pay ranges explain why the prediction uses multiple inputs instead of title alone.")
    chart_close()

    # ── 9. Prediction Studio ─────────────────────────────────────────────
    section_header("Prediction Studio", "teal", "Get a live salary estimate",
                   "Choose a profile and the model predicts an annual salary in USD based on the dataset patterns.")
    left_col, right_col = st.columns([1.1, 0.9], gap="large")

    with left_col:
        st.markdown("<div class='form-shell'>", unsafe_allow_html=True)
        with st.form("prediction_form"):
            experience_level = st.selectbox(
                "Experience level", options=options["experience_level"],
                format_func=humanize_experience_level,
            )
            employment_type = st.selectbox(
                "Employment type", options=options["employment_type"],
                format_func=humanize_employment_type,
            )
            default_jt = options["job_title"].index("Data Scientist") if "Data Scientist" in options["job_title"] else 0
            job_title = st.selectbox("Job title", options=options["job_title"], index=default_jt)
            default_res = options["employee_residence"].index("US") if "US" in options["employee_residence"] else 0
            employee_residence = st.selectbox(
                "Employee residence", options=options["employee_residence"],
                format_func=humanize_country_code, index=default_res,
            )
            default_loc = options["company_location"].index("US") if "US" in options["company_location"] else 0
            company_location = st.selectbox(
                "Company location", options=options["company_location"],
                format_func=humanize_country_code, index=default_loc,
            )
            company_size = st.selectbox(
                "Company size", options=options["company_size"],
                format_func=humanize_company_size,
            )
            remote_ratio = st.selectbox(
                "Work style", options=options["remote_ratio"],
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
        else:
            st.session_state["prediction_payload"] = prediction_payload
            st.session_state["prediction_error"] = None

    with right_col:
        pred = st.session_state["prediction_payload"]
        pred_err = st.session_state["prediction_error"]
        if pred:
            salary = pred["predicted_salary_usd"]
            peer = pred["peer_context"]
            st.markdown(
                f"""<div class="salary-result">
                    <div class="label">Predicted annual salary</div>
                    <div class="amount">${salary:,.0f} <span class="yr">/ year</span></div>
                    <div class="context">Built from {peer['sample_size']} similar records in the dataset.</div>
                    <div class="comparison">{peer['comparison_text']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        elif pred_err:
            st.warning(pred_err)
        else:
            st.info("Start the API, submit the form, and the live prediction will appear here.")

    # ── 10. Explanation section ───────────────────────────────────────────
    section_header("Why This Prediction", "amber",
                   "The data behind the estimate",
                   "How the prediction connects to real salary records, peer benchmarks, and market context.")
    pred = st.session_state["prediction_payload"]
    if pred:
        peer = pred["peer_context"]
        s1, s2, s3 = st.columns(3)
        with s1:
            render_kpi("Peer group", peer["match_label"].title(), 0)
        with s2:
            render_kpi("Typical salary", f"${peer['peer_median_salary_usd']:,.0f}", 1)
        with s3:
            render_kpi("Observed range",
                       f"${peer['peer_min_salary_usd']:,.0f} \u2013 ${peer['peer_max_salary_usd']:,.0f}", 2)

        st.markdown(
            f"<div class='callout amber'>{peer['explanation_summary']}</div>",
            unsafe_allow_html=True,
        )

        d1, d2 = st.columns([1.05, 0.95], gap="large")
        with d1:
            render_drivers(peer["driver_messages"])

        with d2:
            chart_data = build_llm_chart_data(pred, df)
            chart_open("How the estimate compares",
                       "Prediction vs. peer group median vs. broader market median.")
            comp_fig = go.Figure(
                go.Bar(
                    x=chart_data["values"],
                    y=chart_data["labels"],
                    orientation="h",
                    marker_color=[TEAL, AMBER, VIOLET],
                    text=[f"${v:,.0f}" for v in chart_data["values"]],
                    textposition="auto",
                    textfont=dict(color="#FFFFFF", size=13, family="Inter"),
                )
            )
            comp_fig.update_layout(xaxis_title="Salary (USD)", yaxis_title="", height=260)
            st.plotly_chart(apply_chart_style(comp_fig), use_container_width=True, config={"displayModeBar": False})
            chart_close()

            render_ai_card(pred.get("llm_analysis"))
    else:
        st.info("Run a prediction first, then this section will explain the result.")

    # ── 11. History ──────────────────────────────────────────────────────
    history_df, history_error = load_supabase_history()
    if history_df is not None or history_error:
        section_header("History", "violet", "Saved predictions from Supabase",
                       "Every prediction made through the API is persisted. The dashboard reads directly from there.")
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

    # ── 12. Takeaways ────────────────────────────────────────────────────
    section_header("Takeaways", "coral", "Three insights the audience should remember",
                   "Short, presentation-ready points to close the story cleanly.")
    takeaways = build_takeaways(df)
    tw_cols = st.columns(len(takeaways))
    for i, (col, tw) in enumerate(zip(tw_cols, takeaways)):
        with col:
            st.markdown(
                f"""<div class="takeaway t{i}">
                    <div class="num">Takeaway {i + 1}</div>
                    <div class="body">{tw}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── footer ───────────────────────────────────────────────────────────
    st.markdown(
        """<div class="footer">
            <span><span class="name">PayScope</span> &middot; Salary Prediction Dashboard &middot; Yasser Hamdan</span>
        </div>""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
