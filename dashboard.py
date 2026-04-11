from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from analysis import (
    build_peer_context,
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
    get_feature_importances,
    humanize_company_size,
    humanize_country_code,
    humanize_employment_type,
    humanize_experience_level,
    humanize_remote_ratio,
    load_metrics,
    load_model_bundle,
    normalize_prediction_inputs,
    predict_salary,
)


# ── design tokens ────────────────────────────────────────────────────────
INK         = "#07091A"
BG          = "#0A0E1A"
SURFACE     = "#10152A"
SURFACE_HI  = "#161C36"
BORDER      = "rgba(255,255,255,0.07)"
BORDER_HI   = "rgba(255,255,255,0.14)"

TEAL        = "#00E5C3"
CORAL       = "#FF6B6B"
AMBER       = "#FFB547"
VIOLET      = "#A78BFA"
SKY         = "#38BDF8"
LIME        = "#84CC16"
PINK        = "#F472B6"

TEXT        = "#EDF2F7"
MUTED       = "#8892A8"
DIM         = "#5A6378"

CHART_PALETTE = [TEAL, AMBER, VIOLET, SKY, CORAL, LIME, PINK]
CHART_FONT    = {"family": "'Inter', 'Segoe UI', system-ui, sans-serif", "color": TEXT, "size": 12}
CHART_MARGIN  = {"l": 56, "r": 24, "t": 24, "b": 48}

SESSION_DEFAULTS = {
    "prediction_payload": None,
    "prediction_error": None,
}


st.set_page_config(page_title="PayScope", layout="wide", page_icon="$")


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --ink: #07091A;
    --bg: #0A0E1A;
    --surface: #10152A;
    --surface-hi: #161C36;
    --border: rgba(255,255,255,0.07);
    --border-hi: rgba(255,255,255,0.14);
    --teal: #00E5C3;
    --teal-soft: rgba(0,229,195,0.12);
    --teal-line: rgba(0,229,195,0.28);
    --coral: #FF6B6B;
    --amber: #FFB547;
    --violet: #A78BFA;
    --sky: #38BDF8;
    --lime: #84CC16;
    --pink: #F472B6;
    --text: #EDF2F7;
    --muted: #8892A8;
    --dim: #5A6378;
    --mono: 'JetBrains Mono', 'Consolas', 'SF Mono', monospace;
    --sans: 'Inter', 'Segoe UI', system-ui, sans-serif;
    --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
}

html, body, [class*="css"] { font-feature-settings: "ss01", "cv11"; }

.stApp {
    background:
        radial-gradient(1100px 600px at 8% -10%, rgba(0,229,195,0.06), transparent 60%),
        radial-gradient(900px 500px at 100% 0%, rgba(167,139,250,0.045), transparent 60%),
        radial-gradient(800px 500px at 50% 110%, rgba(56,189,248,0.04), transparent 60%),
        var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-feature-settings: "ss01", "cv11";
    -webkit-font-smoothing: antialiased;
}
.block-container {
    max-width: 1240px;
    padding-top: 1.8rem;
    padding-bottom: 5rem;
}

/* ─── hero ───────────────────────────────────────────────────── */
.hero {
    position: relative;
    padding: 3.4rem 0 2.6rem;
    margin-bottom: 3.2rem;
    border-bottom: 1px solid var(--border);
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 56px;
    height: 2px;
    background: var(--teal);
    box-shadow: 0 0 24px rgba(0,229,195,0.6);
}
.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.85rem;
    font-family: var(--mono);
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 1.6rem;
}
.eyebrow .bar {
    display: inline-block;
    width: 28px;
    height: 1px;
    background: var(--teal-line);
}
.hero h1 {
    font-family: var(--sans);
    font-weight: 900;
    font-size: clamp(2.6rem, 6.2vw, 5.2rem);
    line-height: 0.98;
    letter-spacing: -0.035em;
    color: #FFFFFF;
    margin: 0 0 1.4rem;
    max-width: 18ch;
}
.hero h1 em {
    font-style: normal;
    color: var(--teal);
    background: linear-gradient(180deg, var(--teal) 0%, #5EE8D3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-lead {
    color: var(--muted);
    font-size: 1.08rem;
    line-height: 1.7;
    max-width: 62ch;
    margin: 0 0 2.2rem;
    font-weight: 400;
}
.hero-meta {
    display: flex;
    gap: 2.6rem;
    flex-wrap: wrap;
    padding-top: 1.6rem;
    border-top: 1px solid var(--border);
}
.hero-meta .cell { display: flex; flex-direction: column; gap: 0.3rem; }
.hero-meta .k {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--dim);
}
.hero-meta .v {
    font-family: var(--mono);
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--text);
    letter-spacing: 0.02em;
}

/* ─── section headers (editorial, numbered) ─────────────────── */
.section {
    margin: 3.8rem 0 1.6rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}
.section-eyebrow {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    font-family: var(--mono);
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--teal);
}
.section-eyebrow .num { color: var(--dim); }
.section-eyebrow .bar {
    flex: 0 0 32px;
    height: 1px;
    background: var(--teal-line);
}
.section-title {
    font-weight: 800;
    font-size: clamp(1.6rem, 2.5vw, 2.15rem);
    color: #FFFFFF;
    letter-spacing: -0.022em;
    line-height: 1.15;
    margin: 0.15rem 0 0.25rem;
    max-width: 30ch;
}
.section-sub {
    color: var(--muted);
    font-size: 0.98rem;
    line-height: 1.55;
    max-width: 70ch;
    margin: 0 0 0.9rem;
}

/* ─── glass cards (generic) ─────────────────────────────────── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.6rem 1.7rem 1.2rem;
    position: relative;
    transition: border-color 0.25s var(--ease), transform 0.25s var(--ease);
}
.card:hover { border-color: var(--border-hi); }

/* ─── KPI metric cards ──────────────────────────────────────── */
.kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.4rem 1.5rem 1.3rem;
    position: relative;
    overflow: hidden;
    min-height: 132px;
    transition: border-color 0.3s var(--ease);
}
.kpi:hover { border-color: var(--border-hi); }
.kpi::before {
    content: '';
    position: absolute;
    top: 0; left: 1.5rem;
    width: 22px;
    height: 2px;
    background: var(--teal);
}
.kpi .k {
    font-family: var(--mono);
    color: var(--dim);
    font-size: 0.66rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    margin-top: 0.6rem;
    margin-bottom: 0.9rem;
    display: block;
}
.kpi .v {
    font-family: var(--mono);
    color: #FFFFFF;
    font-size: 1.7rem;
    font-weight: 600;
    line-height: 1.05;
    letter-spacing: -0.01em;
}
.kpi .u {
    font-family: var(--mono);
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 500;
    margin-left: 0.25rem;
}

/* ─── chart cards ───────────────────────────────────────────── */
.chart-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.6rem 1.7rem 1.1rem;
    margin-bottom: 1.3rem;
    transition: border-color 0.3s var(--ease);
}
.chart-wrap:hover { border-color: var(--border-hi); }
.chart-head {
    color: #FFFFFF;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.005em;
    margin-bottom: 0.25rem;
}
.chart-desc {
    color: var(--muted);
    font-size: 0.88rem;
    line-height: 1.55;
    margin-bottom: 1rem;
}
.chart-note {
    color: var(--muted);
    font-size: 0.85rem;
    line-height: 1.55;
    margin-top: 0.7rem;
    padding-top: 0.9rem;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 0.7rem;
    align-items: flex-start;
}
.chart-note::before {
    content: '';
    flex: 0 0 14px;
    height: 1px;
    background: var(--teal);
    margin-top: 0.7rem;
}

/* ─── callout (insight) ─────────────────────────────────────── */
.callout {
    display: flex;
    gap: 0.9rem;
    align-items: flex-start;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.1rem 1.3rem;
    font-size: 0.93rem;
    line-height: 1.65;
    color: var(--text);
    margin: 1rem 0 1.4rem;
}
.callout::before {
    content: '';
    flex: 0 0 3px;
    align-self: stretch;
    background: var(--teal);
    border-radius: 3px;
}
.callout strong { color: #FFFFFF; font-weight: 600; }

/* ─── prediction form shell ─────────────────────────────────── */
.form-shell {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 1.8rem 1.7rem 1rem;
    position: relative;
}
.form-shell::before {
    content: 'INPUT';
    position: absolute;
    top: -0.55rem;
    left: 1.6rem;
    padding: 0 0.55rem;
    background: var(--bg);
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.22em;
    color: var(--teal);
}

/* ─── salary result card (the money shot) ──────────────────── */
.salary-result {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 1.8rem 1.8rem 1.7rem;
    min-height: 272px;
    position: relative;
    overflow: hidden;
}
.salary-result::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--teal) 0%, rgba(0,229,195,0) 70%);
}
.salary-result .tag {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 1.1rem;
}
.salary-result .amount {
    font-family: var(--mono);
    font-size: clamp(2.4rem, 5.2vw, 3.4rem);
    font-weight: 600;
    color: #FFFFFF;
    line-height: 1;
    letter-spacing: -0.03em;
    margin-bottom: 0.45rem;
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
}
.salary-result .amount .cur {
    color: var(--teal);
    font-weight: 500;
    font-size: 0.55em;
}
.salary-result .amount .yr {
    color: var(--dim);
    font-size: 0.32em;
    font-weight: 400;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.salary-result .context {
    color: var(--muted);
    font-size: 0.88rem;
    margin-top: 0.5rem;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
    font-family: var(--mono);
    letter-spacing: 0.01em;
}
.salary-result .comparison {
    color: var(--text);
    font-size: 0.95rem;
    line-height: 1.65;
}

/* ─── drivers card ──────────────────────────────────────────── */
.drivers {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.5rem 1.6rem;
}
.drivers .head {
    font-family: var(--mono);
    color: var(--teal);
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
}
.drivers .line {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    padding: 0.55rem 0;
}
.drivers .line + .line { border-top: 1px dashed var(--border); }
.drivers .idx {
    flex: 0 0 auto;
    font-family: var(--mono);
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--dim);
    padding-top: 0.2rem;
    min-width: 1.4rem;
}
.drivers .msg {
    color: var(--text);
    font-size: 0.92rem;
    line-height: 1.6;
}

/* ─── AI insight card ───────────────────────────────────────── */
.ai-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.5rem 1.6rem;
    position: relative;
    overflow: hidden;
}
.ai-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--violet), var(--teal));
}
.ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    font-family: var(--mono);
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--violet);
    margin-bottom: 1rem;
}
.ai-badge .dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--violet);
    box-shadow: 0 0 10px var(--violet);
}
.ai-headline {
    color: #FFFFFF;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.005em;
    margin-bottom: 0.55rem;
    line-height: 1.35;
}
.ai-text {
    color: var(--text);
    font-size: 0.92rem;
    line-height: 1.7;
    margin-bottom: 0.8rem;
}
.ai-list { padding-left: 0; margin: 0; list-style: none; }
.ai-list li {
    position: relative;
    padding-left: 1.1rem;
    color: var(--muted);
    font-size: 0.87rem;
    line-height: 1.6;
    margin-bottom: 0.4rem;
}
.ai-list li::before {
    content: '';
    position: absolute;
    left: 0; top: 0.65rem;
    width: 6px;
    height: 1px;
    background: var(--teal);
}

/* ─── takeaway cards ────────────────────────────────────────── */
.takeaway {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.6rem 1.6rem 1.5rem;
    min-height: 168px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s var(--ease), transform 0.3s var(--ease);
}
.takeaway:hover { border-color: var(--border-hi); transform: translateY(-2px); }
.takeaway .num {
    font-family: var(--mono);
    font-size: 2.4rem;
    font-weight: 500;
    line-height: 1;
    color: var(--teal);
    letter-spacing: -0.02em;
    margin-bottom: 0.9rem;
    display: block;
}
.takeaway .num::after {
    content: '';
    display: block;
    width: 24px;
    height: 1px;
    background: var(--teal);
    margin-top: 0.6rem;
}
.takeaway .body {
    color: var(--text);
    font-size: 0.95rem;
    line-height: 1.6;
}

/* ─── footer ────────────────────────────────────────────────── */
.footer {
    margin-top: 5rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}
.footer .brand {
    font-family: var(--mono);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--teal);
    display: flex;
    align-items: center;
    gap: 0.7rem;
}
.footer .brand::before {
    content: '';
    width: 24px;
    height: 1px;
    background: var(--teal);
}
.footer .meta {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--dim);
}

/* ─── streamlit overrides ───────────────────────────────────── */
.stButton > button {
    background: var(--teal) !important;
    color: #07091A !important;
    font-family: var(--sans) !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.85rem 1.4rem !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    transition: all 0.25s var(--ease) !important;
    box-shadow: 0 0 0 1px rgba(0,229,195,0.2) !important;
}
.stButton > button:hover {
    filter: brightness(1.1) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 30px rgba(0,229,195,0.25), 0 0 0 1px rgba(0,229,195,0.4) !important;
}
div[data-testid="stForm"] { border: none !important; background: transparent !important; }
.stSelectbox label, .stSlider label, .stNumberInput label {
    color: var(--dim) !important;
    font-family: var(--mono) !important;
    font-weight: 500 !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    background: var(--surface-hi) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    font-family: var(--sans) !important;
}
.stSelectbox div[data-baseweb="select"] > div:hover { border-color: var(--border-hi) !important; }
.stDataFrame { border-radius: 16px !important; overflow: hidden !important; border: 1px solid var(--border) !important; }
.stAlert { border-radius: 14px !important; }

/* ─── scroll bar polish ─────────────────────────────────────── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


_CACHED_DATA: tuple[pd.DataFrame, dict[str, Any]] | None = None


def load_cached_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    global _CACHED_DATA
    if _CACHED_DATA is None:
        settings = get_settings()
        _CACHED_DATA = (load_dashboard_data(settings), load_metrics(settings.metrics_path))
    return _CACHED_DATA


def initialize_session_state() -> None:
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, default_value)


def section_header(number: str, eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="section">
            <div class="section-eyebrow">
                <span class="num">{number}</span><span class="bar"></span><span>{eyebrow}</span>
            </div>
            <div class="section-title">{title}</div>
            <div class="section-sub">{subtitle}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str, _index: int = 0) -> None:
    st.markdown(
        f"""<div class="kpi">
            <span class="k">{label}</span>
            <div class="v">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def apply_chart_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=CHART_FONT,
        margin=CHART_MARGIN,
        colorway=CHART_PALETTE,
        hoverlabel=dict(
            bgcolor="#161C36",
            bordercolor="rgba(255,255,255,0.14)",
            font=dict(family="JetBrains Mono, Consolas, monospace", size=12, color="#EDF2F7"),
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.08)",
            tickfont=dict(family="JetBrains Mono, Consolas, monospace", size=11, color="#8892A8"),
            title_font=dict(family="Inter, sans-serif", size=11, color="#5A6378"),
            ticks="outside",
            ticklen=4,
            tickcolor="rgba(255,255,255,0.08)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.08)",
            tickfont=dict(family="JetBrains Mono, Consolas, monospace", size=11, color="#8892A8"),
            title_font=dict(family="Inter, sans-serif", size=11, color="#5A6378"),
        ),
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


_CACHED_MODEL_BUNDLE: dict[str, Any] | None = None
_CACHED_MODEL_BUNDLE_LOADED = False


def get_local_model_bundle():
    global _CACHED_MODEL_BUNDLE, _CACHED_MODEL_BUNDLE_LOADED
    if not _CACHED_MODEL_BUNDLE_LOADED:
        _CACHED_MODEL_BUNDLE_LOADED = True
        settings = get_settings()
        try:
            _CACHED_MODEL_BUNDLE = load_model_bundle(settings.model_path)
        except Exception:
            _CACHED_MODEL_BUNDLE = None
    return _CACHED_MODEL_BUNDLE


def predict_locally(form_payload: dict[str, Any], df: pd.DataFrame) -> dict[str, Any] | None:
    bundle = get_local_model_bundle()
    if bundle is None:
        return None
    normalized = normalize_prediction_inputs(form_payload)
    predicted = predict_salary(bundle, normalized)
    peer = build_peer_context(df, normalized, predicted)
    return {
        "predicted_salary_usd": float(predicted),
        "normalized_inputs": normalized,
        "model_name": bundle.get("model_name", "decision_tree"),
        "peer_context": peer,
        "llm_analysis": None,
    }


def call_prediction_api(
    form_payload: dict[str, Any],
    df: pd.DataFrame,
) -> tuple[dict[str, Any] | None, str | None]:
    settings = get_settings()
    try:
        response = requests.get(
            f"{settings.fastapi_base_url.rstrip('/')}/predict",
            params=form_payload,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json(), None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        fallback = predict_locally(form_payload, df)
        if fallback is not None:
            return fallback, None
        return None, "The API is not reachable and the local model could not be loaded."
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
    for idx, msg in enumerate(driver_messages, start=1):
        lines_html += (
            f'<div class="line"><span class="idx">0{idx}</span>'
            f'<span class="msg">{msg}</span></div>'
        )
    st.markdown(
        f"""<div class="drivers">
            <div class="head">Why this number, specifically</div>
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
                <div class="ai-badge"><span class="dot"></span>The short version</div>
                <div class="ai-headline">{llm_analysis['headline']}</div>
                <div class="ai-text">{llm_analysis['narrative']}</div>
                {insights_html}
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("A plain-English summary will show up here once you get your estimate.")


# ── main ─────────────────────────────────────────────────────────────────

def main() -> None:
    inject_css()
    initialize_session_state()

    settings = get_settings()
    df, metrics = load_cached_data()
    options = get_filter_options(df)

    # ── 1. Hero ──────────────────────────────────────────────────────────
    record_count = f"{len(df):,}"
    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow"><span class="bar"></span>PAYSCOPE &nbsp;/&nbsp; SUNDAY, 11&nbsp;P.M.</div>
            <h1>How much should<br>you <em>actually</em><br>be earning?</h1>
            <p class="hero-lead">
                Sarah asked this on a Sunday night at 11&nbsp;p.m. &mdash; phone in hand, scrolling Reddit,
                with a salary meeting coming Tuesday morning. So can you. No spreadsheets. No jargon.
                Just the real story about pay.
            </p>
            <div class="hero-meta">
                <div class="cell"><span class="k">Real salaries</span><span class="v">{record_count}</span></div>
                <div class="cell"><span class="k">Countries</span><span class="v">70+</span></div>
                <div class="cell"><span class="k">Job titles</span><span class="v">90+</span></div>
                <div class="cell"><span class="k">Your guide</span><span class="v">Yasser Hamdan</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 2. KPI cards ─────────────────────────────────────────────────────
    section_header("01", "The Big Picture", "Let's start with the headlines.",
                   "Four numbers that tell you what's happening in the salary market right now.")
    kpis = get_kpi_snapshot(df)
    kpi_cols = st.columns(len(kpis))
    for i, (col, metric) in enumerate(zip(kpi_cols, kpis)):
        with col:
            render_kpi(metric["label"], metric["value"], i)

    # ── 3. Salary distribution ───────────────────────────────────────────
    section_header("02", "The Shape of Pay", "Where does everyone land?",
                   "Imagine lining up every single person in the data from lowest to highest paid. Here's what that line looks like.")
    chart_open("Where salaries cluster", "The tall bars show where most people sit. The thin tail on the right? That's the lucky few making the big money.")
    hist = px.histogram(
        get_salary_distribution(df), x=TARGET_COLUMN, nbins=30,
        color_discrete_sequence=[TEAL],
    )
    hist.update_traces(marker_line_width=0, marker_line_color=TEAL)
    hist.update_layout(xaxis_title="Annual salary ($)", yaxis_title="How many people", bargap=0.08)
    st.plotly_chart(apply_chart_style(hist), use_container_width=True, config={"displayModeBar": False})
    chart_note("Most salaries cluster in one sweet spot &mdash; but a handful of outliers pull the ceiling way up. Those are the stories everyone wants to hear.")
    chart_close()

    # ── 4. Experience ────────────────────────────────────────────────────
    section_header("03", "Does Experience Pay?", "Spoiler: yes, a lot.",
                   "This is the single clearest pattern in the whole dataset &mdash; and it's not subtle.")

    exp_df = df.copy()
    exp_order = ["EN", "MI", "SE", "EX"]
    exp_df["experience_label"] = exp_df["experience_level"].map(humanize_experience_level)
    chart_open("From entry-level to executive",
               "Each box shows the range of salaries at that career stage. The line in the middle is where most people sit.")
    exp_chart = px.box(
        exp_df, x="experience_label", y=TARGET_COLUMN,
        category_orders={"experience_label": [humanize_experience_level(c) for c in exp_order]},
        color="experience_label",
        color_discrete_sequence=[SKY, TEAL, AMBER, CORAL],
        points=False,
    )
    exp_chart.update_layout(showlegend=False, xaxis_title="", yaxis_title="Annual salary ($)")
    st.plotly_chart(apply_chart_style(exp_chart), use_container_width=True, config={"displayModeBar": False})
    top_exp = get_experience_salary_summary(df).iloc[0]["experience_label"]
    chart_note(f"The jump from junior to senior is huge &mdash; and {top_exp} roles leave everyone else in the dust. Every step up is a real raise.")
    chart_close()

    # ── 5. Employment type ───────────────────────────────────────────────
    section_header("04", "Full-time, Freelance, or In-Between?",
                   "The way you work shapes what you earn.",
                   "Staff jobs, contracts, part-time gigs &mdash; they don't all pay the same. Here's who's winning.")
    chart_open("The winners by work arrangement",
               "Each bar is the typical salary for that kind of worker. Spoiler: it's not what most people think.")
    emp_summary = get_employment_salary_summary(df)
    emp_chart = px.bar(
        emp_summary.sort_values("median", ascending=False),
        x="employment_label", y="median",
        color="employment_label",
        color_discrete_sequence=[TEAL, VIOLET, AMBER, CORAL],
        text="median",
    )
    emp_chart.update_traces(
        marker_line_width=0,
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
        textfont=dict(family="JetBrains Mono", size=12, color=TEXT),
    )
    emp_chart.update_layout(
        showlegend=False, xaxis_title="", yaxis_title="Typical salary ($)", bargap=0.55,
    )
    st.plotly_chart(apply_chart_style(emp_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Full-time salaried work wins the money race &mdash; but contract and freelance life comes with its own freedoms the chart can't show.")
    chart_close()

    # ── 6. Work style ────────────────────────────────────────────────────
    section_header("05", "Office, Hybrid, or Pajamas?",
                   "Does working from home cost you money?",
                   "The eternal debate. We checked the data instead of guessing.")
    chart_open("Where you sit vs. what you make",
               "Compare what people earn when they work in an office, mix it up at home, or go fully remote.")
    remote_summary = get_remote_salary_summary(df)
    remote_chart = px.bar(
        remote_summary, x="remote_label", y="median",
        color="remote_label",
        color_discrete_sequence=[SKY, AMBER, TEAL],
        text="median",
    )
    remote_chart.update_traces(
        marker_line_width=0,
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
        textfont=dict(family="JetBrains Mono", size=12, color=TEXT),
    )
    remote_chart.update_layout(
        showlegend=False, xaxis_title="", yaxis_title="Typical salary ($)", bargap=0.55,
    )
    st.plotly_chart(apply_chart_style(remote_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Remote isn't a pay cut. In many roles, it's the other way around &mdash; the best people can work from anywhere and companies pay for them.")
    chart_close()

    # ── 7. Top roles ─────────────────────────────────────────────────────
    section_header("06", "Which Job Wins?",
                   "The highest-paying titles in the data.",
                   "If you've ever wondered what job title to Google next, start here.")
    chart_open("The best-paid roles in the dataset",
               "Only jobs with enough people in the data to trust the number. Longer bar = bigger paycheck.")
    top_roles = get_top_roles_by_salary(df)
    top_roles_sorted = top_roles.sort_values("median")
    roles_colors = [TEAL, SKY, VIOLET, AMBER, CORAL, LIME, PINK][: len(top_roles_sorted)]
    roles_chart = px.bar(
        top_roles_sorted, x="median", y="job_title", orientation="h",
        color="job_title",
        color_discrete_sequence=roles_colors,
        text="median",
    )
    roles_chart.update_traces(
        marker_line_width=0,
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
        textfont=dict(family="JetBrains Mono", size=11, color=TEXT),
    )
    roles_chart.update_layout(
        showlegend=False, xaxis_title="Typical salary ($)", yaxis_title="", bargap=0.4,
    )
    st.plotly_chart(apply_chart_style(roles_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("The top of the list is dominated by people who turn data and machine learning into business decisions. That's where the market is hungry.")
    chart_close()

    # ── 8. Salary spread ─────────────────────────────────────────────────
    section_header("07", "Same Job, Different Paycheck",
                   "Why two people with identical titles can earn wildly different money.",
                   "Job title is only half the story. Here's proof.")
    chart_open("The wild range inside each role",
               "The wider the box, the bigger the gap between the lowest and highest earners with the exact same title.")
    spread_df = get_role_spread_data(df)
    spread_chart = px.box(
        spread_df, x=TARGET_COLUMN, y="job_title",
        color="job_title",
        color_discrete_sequence=CHART_PALETTE,
        points=False,
    )
    spread_chart.update_layout(showlegend=False, xaxis_title="Annual salary ($)", yaxis_title="")
    st.plotly_chart(apply_chart_style(spread_chart), use_container_width=True, config={"displayModeBar": False})
    chart_note("Same title, very different pay. Why? Experience. Country. Company size. Negotiation. PayScope weighs all of them together.")
    chart_close()

    # ── 9. Prediction Studio ─────────────────────────────────────────────
    section_header("08", "Your Turn — Just Like Sarah",
                   "She filled this in on Sunday night. Now it's your turn.",
                   "Tell us a bit about you. Hit the button. Meet your number — and the story behind it.")
    left_col, right_col = st.columns([1.1, 0.9], gap="large")

    with left_col:
        st.markdown("<div class='form-shell'>", unsafe_allow_html=True)
        with st.form("prediction_form"):
            experience_level = st.selectbox(
                "How experienced are you?", options=options["experience_level"],
                format_func=humanize_experience_level,
            )
            employment_type = st.selectbox(
                "What kind of job?", options=options["employment_type"],
                format_func=humanize_employment_type,
            )
            default_jt = options["job_title"].index("Data Scientist") if "Data Scientist" in options["job_title"] else 0
            job_title = st.selectbox("What's your role?", options=options["job_title"], index=default_jt)
            default_res = options["employee_residence"].index("US") if "US" in options["employee_residence"] else 0
            employee_residence = st.selectbox(
                "Where do you live?", options=options["employee_residence"],
                format_func=humanize_country_code, index=default_res,
            )
            default_loc = options["company_location"].index("US") if "US" in options["company_location"] else 0
            company_location = st.selectbox(
                "Where's the company?", options=options["company_location"],
                format_func=humanize_country_code, index=default_loc,
            )
            company_size = st.selectbox(
                "How big is the company?", options=options["company_size"],
                format_func=humanize_company_size,
            )
            remote_ratio = st.selectbox(
                "Where do you work from?", options=options["remote_ratio"],
                format_func=humanize_remote_ratio,
            )
            submitted = st.form_submit_button("Show me the number", use_container_width=True)
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
        prediction_payload, error_message = call_prediction_api(payload, df)
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
                    <div class="tag">Your estimated salary</div>
                    <div class="amount"><span class="cur">$</span>{salary:,.0f}<span class="yr">/ year</span></div>
                    <div class="context">Based on {peer['sample_size']} people just like you</div>
                    <div class="comparison">{peer['comparison_text']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        elif pred_err:
            st.warning(pred_err)
        else:
            st.info("Fill in the form and tap the button to see your number.")

    # ── 10. Explanation section ───────────────────────────────────────────
    section_header("09", "Where This Number Came From",
                   "No black box. Here's the story.",
                   "We found real people just like you in the data and looked at what they actually earn.")
    pred = st.session_state["prediction_payload"]
    if pred:
        peer = pred["peer_context"]
        s1, s2, s3 = st.columns(3)
        with s1:
            render_kpi("People like you", peer["match_label"].title(), 0)
        with s2:
            render_kpi("What they typically earn", f"${peer['peer_median_salary_usd']:,.0f}", 1)
        with s3:
            render_kpi("From lowest to highest",
                       f"${peer['peer_min_salary_usd']:,.0f} \u2013 ${peer['peer_max_salary_usd']:,.0f}", 2)

        st.markdown(
            f"<div class='callout'>{peer['explanation_summary']}</div>",
            unsafe_allow_html=True,
        )

        d1, d2 = st.columns([1.05, 0.95], gap="large")
        with d1:
            render_drivers(peer["driver_messages"])

        with d2:
            chart_data = build_llm_chart_data(pred, df)
            friendly_labels = ["You", "People like you", "Everyone else"]
            chart_open("How you stack up",
                       "Your estimate next to people in your situation, and next to the whole market. See where you land.")
            comp_fig = go.Figure(
                go.Bar(
                    x=chart_data["values"],
                    y=friendly_labels,
                    orientation="h",
                    marker_color=[TEAL, VIOLET, SKY],
                    text=[f"${v:,.0f}" for v in chart_data["values"]],
                    textposition="outside",
                    cliponaxis=False,
                    textfont=dict(color="#EDF2F7", size=12, family="JetBrains Mono"),
                )
            )
            comp_fig.update_layout(xaxis_title="Annual salary ($)", yaxis_title="", height=280, bargap=0.5)
            st.plotly_chart(apply_chart_style(comp_fig), use_container_width=True, config={"displayModeBar": False})
            chart_close()

            render_ai_card(pred.get("llm_analysis"))
    else:
        st.info("Get your estimate first &mdash; then we'll break it down for you.")

    # ── 11. Feature Influence ────────────────────────────────────────────
    if pred:
        section_header("10", "What Moved the Needle",
                       "Which parts of your profile mattered most?",
                       "Some things shift your salary by a lot. Others barely budge it. Here's the ranking.")
        bundle = get_local_model_bundle()
        if bundle is not None:
            importances = get_feature_importances(bundle)
            user_inputs = {
                "job_title": job_title,
                "experience_level": humanize_experience_level(experience_level),
                "employment_type": humanize_employment_type(employment_type),
                "employee_residence": humanize_country_code(employee_residence),
                "company_location": humanize_country_code(company_location),
                "company_size": humanize_company_size(company_size),
                "remote_ratio": humanize_remote_ratio(remote_ratio),
            }
            chart_open("What shaped your number",
                       "The biggest bar had the biggest say. Change it and your estimate moves a lot. Tiny bars? Barely matter.")
            imp_labels = [row["label"] for row in importances]
            imp_values = [row["pct"] for row in importances]
            imp_hover = [
                f"<b>{row['label']}</b><br>Your pick: {user_inputs.get(row['feature'], '—')}"
                f"<br>Weight: {row['pct']}%"
                for row in importances
            ]
            imp_palette = [TEAL, VIOLET, SKY, AMBER, CORAL, LIME, PINK]
            imp_colors = [imp_palette[i % len(imp_palette)] for i in range(len(imp_values))]
            imp_fig = go.Figure(
                go.Bar(
                    x=imp_values,
                    y=imp_labels,
                    orientation="h",
                    marker=dict(color=imp_colors, line=dict(width=0)),
                    text=[f"{v}%" for v in imp_values],
                    textposition="outside",
                    cliponaxis=False,
                    textfont=dict(color="#EDF2F7", size=12, family="JetBrains Mono"),
                    hovertext=imp_hover,
                    hoverinfo="text",
                )
            )
            imp_fig.update_layout(
                xaxis_title="How much it mattered (%)",
                yaxis_title="",
                height=360,
                bargap=0.45,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(apply_chart_style(imp_fig), use_container_width=True,
                            config={"displayModeBar": False})
            top = importances[0]
            chart_note(
                f"{top['label']} alone shaped {top['pct']}% of your number. "
                f"That's why switching country or seniority can change your estimate so dramatically."
            )
            chart_close()

    # ── 12. History ──────────────────────────────────────────────────────
    history_df, history_error = load_supabase_history()
    if history_df is not None or history_error:
        section_header("11", "Recent Estimates",
                       "What other people have been checking lately.",
                       "Every estimate is saved so you can see who's asking what. Anonymous, of course.")
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
    section_header("12", "What to Remember",
                   "If you close this tab right now, take these three things with you.",
                   "The whole salary story, in three sentences.")
    takeaways = build_takeaways(df)
    tw_cols = st.columns(len(takeaways))
    for i, (col, tw) in enumerate(zip(tw_cols, takeaways)):
        with col:
            st.markdown(
                f"""<div class="takeaway">
                    <span class="num">0{i + 1}</span>
                    <div class="body">{tw}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── footer ───────────────────────────────────────────────────────────
    st.markdown(
        """<div class="footer">
            <span class="brand">PAYSCOPE</span>
            <span class="meta">Salary Intelligence &nbsp;/&nbsp; Yasser Hamdan &nbsp;/&nbsp; 2026</span>
        </div>""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
