"""Generate the PayScope presentation deck — vibrant, chart-heavy, animated."""
from __future__ import annotations

import copy
import math
from lxml import etree

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.chart.data import CategoryChartData

# ── colour palette (matches new dashboard) ───────────────────────────────
BG        = RGBColor(0x0A, 0x0E, 0x1A)
SURFACE   = RGBColor(0x12, 0x17, 0x2B)
SURF_ALT  = RGBColor(0x19, 0x1F, 0x38)
TEAL      = RGBColor(0x00, 0xE5, 0xC3)
TEAL_DIM  = RGBColor(0x00, 0x99, 0x83)
CORAL     = RGBColor(0xFF, 0x6B, 0x6B)
AMBER     = RGBColor(0xFF, 0xB5, 0x47)
VIOLET    = RGBColor(0xA7, 0x8B, 0xFA)
SKY       = RGBColor(0x38, 0xBD, 0xF8)
LIME      = RGBColor(0x84, 0xCC, 0x16)
PINK      = RGBColor(0xF4, 0x72, 0xB6)
WHITE     = RGBColor(0xED, 0xF2, 0xF7)
MUTED     = RGBColor(0x8B, 0x95, 0xA8)
DARK      = RGBColor(0x0A, 0x0E, 0x1A)

W = Inches(13.333)
H = Inches(7.5)

NSMAP = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


# ── helpers ──────────────────────────────────────────────────────────────

def set_bg(slide, color=BG):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def rect(slide, l, t, w, h, color, radius=0.06):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    if s.adjustments and len(s.adjustments) > 0:
        s.adjustments[0] = radius
    return s


def circle(slide, l, t, size, color, alpha=None):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, l, t, size, size)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    if alpha is not None:
        _set_shape_alpha(s, alpha)
    return s


def _set_shape_alpha(shape, alpha_pct):
    """Set fill transparency 0-100 (0=opaque, 100=fully transparent)."""
    spPr = shape._element.spPr
    solidFill = spPr.find(".//a:solidFill", NSMAP)
    if solidFill is not None:
        srgb = solidFill.find("a:srgbClr", NSMAP)
        if srgb is not None:
            existing = srgb.findall("a:alpha", NSMAP)
            for e in existing:
                srgb.remove(e)
            alpha_el = etree.SubElement(srgb, f"{{{NSMAP['a']}}}alpha")
            alpha_el.set("val", str(int((100 - alpha_pct) * 1000)))


def bar(slide, l, t, w, h, color):
    """Simple rectangle bar (no rounding)."""
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    return s


def line_shape(slide, l, t, w, h, color):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    return s


def txt(slide, l, t, w, h, text, sz, color=WHITE, bold=False, align=PP_ALIGN.LEFT, font="Segoe UI"):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(sz)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font
    p.alignment = align
    return tb


def multi(slide, l, t, w, h, lines):
    """lines = [(text, size, color, bold), ...]"""
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (text, sz, color, bold) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.font.size = Pt(sz)
        p.font.color.rgb = color
        p.font.bold = bold
        p.font.name = "Segoe UI"
        p.space_after = Pt(5)
    return tb


def pill(slide, l, t, text, bg_color, txt_color=DARK, w=Inches(1.8)):
    s = rect(slide, l, t, w, Inches(0.36), bg_color, radius=0.15)
    tf = s.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(10)
    p.font.color.rgb = txt_color
    p.font.bold = True
    p.font.name = "Segoe UI"
    p.alignment = PP_ALIGN.CENTER
    return s


def glow_circle(slide, cx, cy, r, color, alpha=85):
    """Decorative translucent circle."""
    return circle(slide, cx - r, cy - r, r * 2, color, alpha)


def add_decorative_dots(slide, x_start, y_start, cols, rows, gap, color, alpha=88):
    """Grid of tiny translucent dots for visual texture."""
    for r in range(rows):
        for c in range(cols):
            circle(slide, x_start + c * gap, y_start + r * gap,
                   Inches(0.06), color, alpha)


def add_entrance_anim(slide, shape, delay_ms=0, dur_ms=500, effect="fade"):
    """Add a PowerPoint entrance animation to a shape."""
    slide_element = slide._element
    timing = slide_element.find(f"{{{NSMAP['p']}}}timing")
    if timing is None:
        timing = etree.SubElement(slide_element, f"{{{NSMAP['p']}}}timing")

    tnLst = timing.find(f"{{{NSMAP['p']}}}tnLst")
    if tnLst is None:
        tnLst = etree.SubElement(timing, f"{{{NSMAP['p']}}}tnLst")

    par = tnLst.find(f"{{{NSMAP['p']}}}par")
    if par is None:
        par = etree.SubElement(tnLst, f"{{{NSMAP['p']}}}par")
        cTn_root = etree.SubElement(par, f"{{{NSMAP['p']}}}cTn", attrib={
            "id": "1", "dur": "indefinite", "restart": "never", "nodeType": "tmRoot"
        })
        childTnLst = etree.SubElement(cTn_root, f"{{{NSMAP['p']}}}childTnLst")
        seq = etree.SubElement(childTnLst, f"{{{NSMAP['p']}}}seq", attrib={
            "concurrent": "1", "nextAc": "seek"
        })
        seq_cTn = etree.SubElement(seq, f"{{{NSMAP['p']}}}cTn", attrib={
            "id": "2", "dur": "indefinite", "nodeType": "mainSeq"
        })
        seq_childTnLst = etree.SubElement(seq_cTn, f"{{{NSMAP['p']}}}childTnLst")
    else:
        cTn_root = par.find(f"{{{NSMAP['p']}}}cTn")
        childTnLst = cTn_root.find(f"{{{NSMAP['p']}}}childTnLst")
        seq = childTnLst.find(f"{{{NSMAP['p']}}}seq")
        seq_cTn = seq.find(f"{{{NSMAP['p']}}}cTn")
        seq_childTnLst = seq_cTn.find(f"{{{NSMAP['p']}}}childTnLst")

    existing_pars = seq_childTnLst.findall(f"{{{NSMAP['p']}}}par")
    next_id = 3 + len(existing_pars) * 10

    shape_id = shape.shape_id

    outer_par = etree.SubElement(seq_childTnLst, f"{{{NSMAP['p']}}}par")
    outer_cTn = etree.SubElement(outer_par, f"{{{NSMAP['p']}}}cTn", attrib={
        "id": str(next_id), "fill": "hold"
    })
    stCondLst = etree.SubElement(outer_cTn, f"{{{NSMAP['p']}}}stCondLst")
    cond = etree.SubElement(stCondLst, f"{{{NSMAP['p']}}}cond", attrib={"delay": "0"})
    if len(existing_pars) == 0:
        cond.set("evt", "onNext")
        cond.set("delay", "0")
        tgtEl = etree.SubElement(cond, f"{{{NSMAP['p']}}}tgtEl")
        sldTgt = etree.SubElement(tgtEl, f"{{{NSMAP['p']}}}sldTgt")
    else:
        cond.set("delay", "0")

    outer_childTnLst = etree.SubElement(outer_cTn, f"{{{NSMAP['p']}}}childTnLst")

    inner_par = etree.SubElement(outer_childTnLst, f"{{{NSMAP['p']}}}par")
    inner_cTn = etree.SubElement(inner_par, f"{{{NSMAP['p']}}}cTn", attrib={
        "id": str(next_id + 1), "presetID": "10" if effect == "fade" else "2",
        "presetClass": "entr", "presetSubtype": "0",
        "fill": "hold", "grpId": "0", "nodeType": "withEffect"
    })
    inner_stCondLst = etree.SubElement(inner_cTn, f"{{{NSMAP['p']}}}stCondLst")
    inner_cond = etree.SubElement(inner_stCondLst, f"{{{NSMAP['p']}}}cond", attrib={
        "delay": str(delay_ms)
    })
    inner_childTnLst = etree.SubElement(inner_cTn, f"{{{NSMAP['p']}}}childTnLst")

    # animEffect
    animEffect = etree.SubElement(inner_childTnLst, f"{{{NSMAP['p']}}}animEffect", attrib={
        "transition": "in", "filter": "fade" if effect == "fade" else "blinds(horizontal)"
    })
    ae_cBhvr = etree.SubElement(animEffect, f"{{{NSMAP['p']}}}cBhvr")
    ae_cTn = etree.SubElement(ae_cBhvr, f"{{{NSMAP['p']}}}cTn", attrib={
        "id": str(next_id + 2), "dur": str(dur_ms)
    })
    ae_tgtEl = etree.SubElement(ae_cBhvr, f"{{{NSMAP['p']}}}tgtEl")
    ae_spTgt = etree.SubElement(ae_tgtEl, f"{{{NSMAP['p']}}}spTgt", attrib={
        "spid": str(shape_id)
    })


def add_pptx_chart(slide, chart_type, categories, series_data, l, t, w, h, colors=None):
    """Add a native PowerPoint chart. series_data = [(name, [values]), ...]"""
    chart_data = CategoryChartData()
    chart_data.categories = categories
    for name, values in series_data:
        chart_data.add_series(name, values)

    chart_frame = slide.shapes.add_chart(chart_type, l, t, w, h, chart_data)
    chart = chart_frame.chart
    chart.has_legend = False

    plot = chart.plots[0]
    plot.gap_width = 80

    if colors and chart_type in (XL_CHART_TYPE.COLUMN_CLUSTERED, XL_CHART_TYPE.BAR_CLUSTERED):
        for s_idx, series in enumerate(plot.series):
            if len(series_data) == 1 and colors:
                for pt_idx in range(len(categories)):
                    pt = series.points[pt_idx]
                    pt.format.fill.solid()
                    pt.format.fill.fore_color.rgb = colors[pt_idx % len(colors)]
            else:
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = colors[s_idx % len(colors)]

    chart.chart_style = 2
    chart_frame.chart.plot_area = chart.plot_area

    # style the chart area
    chart.element.find(".//" + "{http://schemas.openxmlformats.org/drawingml/2006/chart}chartSpace", )

    return chart_frame


def style_chart_dark(chart_frame):
    """Make chart background transparent and text light."""
    chart = chart_frame.chart
    # chart area fill
    chart.chart_style = 2
    fa = chart.element
    # Try to set dark styling via XML
    for text_elem in fa.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t"):
        pass  # text color handled by chart style
    return chart_frame


# ── decorative background elements ──────────────────────────────────────

def deco_top_right(slide):
    glow_circle(slide, Inches(10.5), Inches(-1.2), Inches(2.5), TEAL, 92)
    glow_circle(slide, Inches(11.2), Inches(-0.5), Inches(1.5), VIOLET, 94)


def deco_bottom_left(slide):
    glow_circle(slide, Inches(-1.0), Inches(5.5), Inches(2.2), CORAL, 93)
    glow_circle(slide, Inches(0.2), Inches(6.0), Inches(1.0), AMBER, 95)


def deco_corners(slide):
    deco_top_right(slide)
    deco_bottom_left(slide)


def deco_dots_right(slide):
    add_decorative_dots(slide, Inches(11.0), Inches(1.5), 5, 8, Inches(0.22), TEAL, 90)


def deco_dots_left(slide):
    add_decorative_dots(slide, Inches(0.8), Inches(5.0), 4, 4, Inches(0.22), VIOLET, 91)


# ── slide builders ───────────────────────────────────────────────────────

def slide_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)

    # decorative glow orbs
    glow_circle(slide, Inches(8.5), Inches(-2), Inches(5), TEAL, 93)
    glow_circle(slide, Inches(-2), Inches(4), Inches(4), CORAL, 94)
    glow_circle(slide, Inches(10), Inches(5), Inches(3), VIOLET, 95)
    glow_circle(slide, Inches(1), Inches(-1.5), Inches(3), AMBER, 96)

    # decorative dots
    add_decorative_dots(slide, Inches(10.2), Inches(1.0), 6, 10, Inches(0.25), TEAL, 88)
    add_decorative_dots(slide, Inches(0.6), Inches(5.5), 4, 4, Inches(0.25), CORAL, 90)

    # colored accent line
    line_shape(slide, Inches(1.2), Inches(2.2), Inches(0.5), Inches(0.07), TEAL)
    line_shape(slide, Inches(1.8), Inches(2.2), Inches(0.5), Inches(0.07), CORAL)
    line_shape(slide, Inches(2.4), Inches(2.2), Inches(0.5), Inches(0.07), AMBER)

    # title
    title_shape = txt(slide, Inches(1.2), Inches(2.6), Inches(9), Inches(1.3),
                      "PayScope", 60, TEAL, True)
    add_entrance_anim(slide, title_shape, 0, 800, "fade")

    sub = txt(slide, Inches(1.2), Inches(3.8), Inches(9), Inches(0.9),
              "Predict, explain, and compare data-science salaries.", 28, WHITE, False)
    add_entrance_anim(slide, sub, 300, 600, "fade")

    info = txt(slide, Inches(1.2), Inches(4.8), Inches(9), Inches(0.6),
               "Yasser Hamdan   |   Week 1   |   AI Engineering Program", 16, MUTED)
    add_entrance_anim(slide, info, 600, 500, "fade")

    # small stat pills at bottom
    stats = [
        ("607 Records", TEAL), ("7 Features", AMBER),
        ("Decision Tree", CORAL), ("Live API", VIOLET),
    ]
    for i, (label, color) in enumerate(stats):
        p = pill(slide, Inches(1.2 + i * 2.2), Inches(5.8), label, color, DARK, w=Inches(1.9))
        add_entrance_anim(slide, p, 800 + i * 150, 400, "fade")


def slide_problem(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    deco_corners(slide)

    pill(slide, Inches(0.8), Inches(0.5), "THE PROBLEM", CORAL, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.9),
        "Salary data is scattered, inconsistent, and hard to interpret.", 32, WHITE, True)
    txt(slide, Inches(0.8), Inches(2.05), Inches(11), Inches(0.5),
        "Data professionals need a quick, reliable way to benchmark compensation.", 17, MUTED)

    # three visual cards with colored left-border accent
    cards = [
        (TEAL,  "Job Seekers",     "\"What should I expect\nto earn in my next role?\"",       "$"),
        (AMBER, "Hiring Managers", "\"Am I offering a competitive\nsalary for this market?\"",  "~"),
        (CORAL, "The Dataset",     "~607 real salary records\nfrom Kaggle DS Salaries",         "#"),
    ]
    for i, (color, title, body, icon) in enumerate(cards):
        x = Inches(0.8 + i * 3.95)
        y = Inches(3.1)
        # card bg
        c = rect(slide, x, y, Inches(3.6), Inches(3.2), SURFACE, 0.05)
        add_entrance_anim(slide, c, 200 + i * 250, 500, "fade")
        # left accent bar
        line_shape(slide, x, y + Inches(0.15), Inches(0.06), Inches(2.9), color)
        # icon circle
        ic = circle(slide, x + Inches(0.35), y + Inches(0.35), Inches(0.7), color, 80)
        txt(slide, x + Inches(0.35), y + Inches(0.35), Inches(0.7), Inches(0.7),
            icon, 26, color, True, PP_ALIGN.CENTER)
        # title
        txt(slide, x + Inches(0.35), y + Inches(1.2), Inches(2.9), Inches(0.45),
            title, 19, color, True)
        # body
        txt(slide, x + Inches(0.35), y + Inches(1.7), Inches(2.9), Inches(1.2),
            body, 14, MUTED)


def slide_architecture(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    deco_dots_right(slide)
    glow_circle(slide, Inches(-1), Inches(2), Inches(3), VIOLET, 94)

    pill(slide, Inches(0.8), Inches(0.5), "ARCHITECTURE", VIOLET, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "One call does everything: predict > explain > persist", 28, WHITE, True)

    # pipeline boxes with individual colors
    steps = [
        ("CSV Data",   "607 salary\nrecords",       TEAL,   "1"),
        ("ML Model",   "Decision Tree\nscikit-learn", AMBER, "2"),
        ("FastAPI",    "GET /predict\n+ Ollama LLM",  CORAL, "3"),
        ("Supabase",   "Persist every\nprediction",   VIOLET,"4"),
        ("Dashboard",  "Streamlit\ncharts + story",   SKY,   "5"),
    ]
    box_w = Inches(2.05)
    box_h = Inches(2.5)
    start_x = Inches(0.5)
    y = Inches(2.5)
    gap = Inches(0.38)

    for i, (title, body, color, num) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        # card
        c = rect(slide, x, y, box_w, box_h, SURFACE, 0.06)
        add_entrance_anim(slide, c, i * 200, 500, "fade")
        # top color bar
        line_shape(slide, x + Inches(0.1), y + Inches(0.08), box_w - Inches(0.2), Inches(0.045), color)
        # number badge
        nc = circle(slide, x + Inches(0.7), y + Inches(0.35), Inches(0.55), color)
        txt(slide, x + Inches(0.7), y + Inches(0.35), Inches(0.55), Inches(0.55),
            num, 18, DARK, True, PP_ALIGN.CENTER)
        # title
        txt(slide, x + Inches(0.1), y + Inches(1.05), box_w - Inches(0.2), Inches(0.4),
            title, 16, WHITE, True, PP_ALIGN.CENTER)
        # body
        txt(slide, x + Inches(0.1), y + Inches(1.5), box_w - Inches(0.2), Inches(0.8),
            body, 12, MUTED, False, PP_ALIGN.CENTER)

        # arrow
        if i < len(steps) - 1:
            ax = x + box_w + Inches(0.04)
            txt(slide, ax, y + Inches(0.95), Inches(0.3), Inches(0.4),
                ">", 26, color, True, PP_ALIGN.CENTER)

    # deployment badge row
    deploy = [("Railway", CORAL), ("Streamlit Cloud", SKY), ("Supabase", VIOLET)]
    for i, (label, color) in enumerate(deploy):
        pill(slide, Inches(2.5 + i * 3.0), Inches(5.5), label, color, DARK, w=Inches(2.2))


def slide_data_stats(prs):
    """Data overview slide with big numbers and a native chart."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    deco_corners(slide)

    pill(slide, Inches(0.8), Inches(0.5), "THE DATA", AMBER, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "607 real salaries, 7 features, 1 target", 28, WHITE, True)

    # big stat cards — left side
    stats = [
        ("607", "Total records", TEAL),
        ("$101,570", "Median salary", AMBER),
        ("7", "Input features", CORAL),
        ("$112,297", "Mean salary", VIOLET),
    ]
    for i, (val, label, color) in enumerate(stats):
        col = i % 2
        row = i // 2
        x = Inches(0.8 + col * 2.7)
        y = Inches(2.3 + row * 2.2)
        c = rect(slide, x, y, Inches(2.4), Inches(1.85), SURFACE, 0.06)
        add_entrance_anim(slide, c, i * 200, 400, "fade")
        # top bar
        line_shape(slide, x + Inches(0.1), y + Inches(0.08), Inches(2.2), Inches(0.04), color)
        # value
        txt(slide, x + Inches(0.25), y + Inches(0.35), Inches(2.0), Inches(0.8),
            val, 32, color, True, PP_ALIGN.CENTER, "Segoe UI")
        # label
        txt(slide, x + Inches(0.25), y + Inches(1.2), Inches(2.0), Inches(0.4),
            label, 13, MUTED, False, PP_ALIGN.CENTER)

    # right side: native bar chart — experience vs salary
    chart_data = CategoryChartData()
    chart_data.categories = ["Entry", "Mid", "Senior", "Executive"]
    chart_data.add_series("Median Salary", [56500, 76940, 135500, 171438])

    cf = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(6.4), Inches(2.3), Inches(6.0), Inches(4.3),
        chart_data,
    )
    chart = cf.chart
    chart.has_legend = False
    plot = chart.plots[0]
    plot.gap_width = 100

    # color each bar differently
    colors = [TEAL, AMBER, CORAL, VIOLET]
    series = plot.series[0]
    for idx in range(4):
        pt = series.points[idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = colors[idx]

    # data labels
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(11)
    dl.font.color.rgb = WHITE
    dl.font.bold = True
    dl.number_format = '$#,##0'
    dl.show_value = True

    add_entrance_anim(slide, cf, 600, 700, "fade")

    txt(slide, Inches(6.4), Inches(6.7), Inches(6.0), Inches(0.4),
        "Median salary by experience level (from actual dataset)", 12, MUTED, False, PP_ALIGN.CENTER)


def slide_model(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    glow_circle(slide, Inches(11), Inches(-1), Inches(2.5), AMBER, 93)
    deco_dots_left(slide)

    pill(slide, Inches(0.8), Inches(0.5), "THE MODEL", LIME, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "Decision Tree - interpretable and fast", 28, WHITE, True)

    # left: pipeline visual as stacked cards
    pipe_steps = [
        ("1", "OneHotEncoder", "Converts categories to numbers", TEAL),
        ("2", "DecisionTreeRegressor", "max_depth=12, min_samples_leaf=4", AMBER),
        ("3", "Joblib Artifact", "One file, ready to deploy anywhere", CORAL),
    ]
    for i, (num, title, desc, color) in enumerate(pipe_steps):
        y = Inches(2.3 + i * 1.55)
        c = rect(slide, Inches(0.8), y, Inches(5.5), Inches(1.3), SURFACE, 0.05)
        add_entrance_anim(slide, c, i * 300, 500, "fade")
        line_shape(slide, Inches(0.8), y + Inches(0.08), Inches(5.5), Inches(0.04), color)
        # number circle
        circle(slide, Inches(1.1), y + Inches(0.3), Inches(0.55), color)
        txt(slide, Inches(1.1), y + Inches(0.3), Inches(0.55), Inches(0.55),
            num, 18, DARK, True, PP_ALIGN.CENTER)
        txt(slide, Inches(1.9), y + Inches(0.25), Inches(4.0), Inches(0.4),
            title, 17, WHITE, True)
        txt(slide, Inches(1.9), y + Inches(0.7), Inches(4.0), Inches(0.4),
            desc, 13, MUTED)

    # right: "Why Decision Tree?" card
    rect(slide, Inches(6.8), Inches(2.3), Inches(5.7), Inches(4.65), SURFACE, 0.05)
    line_shape(slide, Inches(6.8), Inches(2.38), Inches(5.7), Inches(0.04), LIME)
    txt(slide, Inches(7.1), Inches(2.55), Inches(5.0), Inches(0.4),
        "Why Decision Tree?", 20, LIME, True)

    reasons = [
        ("Interpretable", "Every split is explainable to a non-technical audience", TEAL),
        ("Handles mixed data", "Categorical + numerical features natively", AMBER),
        ("Fast training", "~600 records train in under a second", CORAL),
        ("No black box", "Perfect for a demo you need to defend", VIOLET),
    ]
    for i, (title, desc, color) in enumerate(reasons):
        y = Inches(3.2 + i * 0.9)
        circle(slide, Inches(7.1), y + Inches(0.05), Inches(0.25), color)
        txt(slide, Inches(7.1), y + Inches(0.05), Inches(0.25), Inches(0.25),
            "+", 12, DARK, True, PP_ALIGN.CENTER)
        txt(slide, Inches(7.55), y, Inches(4.5), Inches(0.35),
            title, 15, WHITE, True)
        txt(slide, Inches(7.55), y + Inches(0.35), Inches(4.5), Inches(0.35),
            desc, 12, MUTED)

    # model metrics
    rect(slide, Inches(6.8), Inches(5.65), Inches(5.7), Inches(1.3), SURF_ALT, 0.05)
    txt(slide, Inches(7.1), Inches(5.8), Inches(2.0), Inches(0.35), "Model Metrics", 14, MUTED, True)
    metrics_items = [("R\u00b2", "0.448", TEAL), ("RMSE", "$46,003", AMBER), ("MAE", "$32,197", CORAL)]
    for i, (label, val, color) in enumerate(metrics_items):
        x = Inches(7.1 + i * 1.8)
        txt(slide, x, Inches(6.2), Inches(1.5), Inches(0.35), val, 20, color, True)
        txt(slide, x, Inches(6.55), Inches(1.5), Inches(0.25), label, 11, MUTED)


def slide_top_roles(prs):
    """Chart slide: top-paying roles."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    glow_circle(slide, Inches(11), Inches(5), Inches(2), SKY, 94)
    glow_circle(slide, Inches(-1), Inches(-1), Inches(2.5), LIME, 95)

    pill(slide, Inches(0.8), Inches(0.5), "TOP ROLES", SKY, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "Which job titles earn the most?", 28, WHITE, True)
    txt(slide, Inches(0.8), Inches(1.85), Inches(11), Inches(0.4),
        "Only roles with 8+ data points included for reliability.", 16, MUTED)

    # native horizontal bar chart
    roles = ["Data Analyst", "Data Scientist", "Data Engineer",
             "DS Manager", "ML Scientist", "Data Architect"]
    salaries = [90320, 103691, 105500, 155750, 156500, 180000]

    chart_data = CategoryChartData()
    chart_data.categories = roles
    chart_data.add_series("Median Salary", salaries)

    cf = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(0.8), Inches(2.6), Inches(7.5), Inches(4.3),
        chart_data,
    )
    chart = cf.chart
    chart.has_legend = False
    plot = chart.plots[0]
    plot.gap_width = 80

    bar_colors = [TEAL, SKY, AMBER, CORAL, VIOLET, LIME]
    series = plot.series[0]
    for idx in range(6):
        pt = series.points[idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = bar_colors[idx]

    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(11)
    dl.font.color.rgb = WHITE
    dl.font.bold = True
    dl.number_format = '$#,##0'
    dl.show_value = True

    add_entrance_anim(slide, cf, 300, 700, "fade")

    # right side: quick insight cards
    insights = [
        ("Data Architect", "$180K median", "Highest-paying role\nin the dataset", LIME),
        ("Data Scientist", "$103K median", "143 records -\nmost common role", SKY),
        ("2x gap", "Analyst vs Architect", "Title matters before\nwe add experience", CORAL),
    ]
    for i, (title, val, desc, color) in enumerate(insights):
        y = Inches(2.6 + i * 1.5)
        c = rect(slide, Inches(8.8), y, Inches(3.8), Inches(1.25), SURFACE, 0.05)
        add_entrance_anim(slide, c, 700 + i * 200, 400, "fade")
        line_shape(slide, Inches(8.8), y + Inches(0.08), Inches(0.06), Inches(1.1), color)
        txt(slide, Inches(9.15), y + Inches(0.15), Inches(3.2), Inches(0.3),
            title, 14, color, True)
        txt(slide, Inches(9.15), y + Inches(0.45), Inches(3.2), Inches(0.3),
            val, 16, WHITE, True)
        txt(slide, Inches(9.15), y + Inches(0.78), Inches(3.2), Inches(0.4),
            desc, 11, MUTED)


def slide_demo(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    deco_corners(slide)

    pill(slide, Inches(0.8), Inches(0.5), "LIVE DEMO", TEAL, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "Let me show you PayScope in action", 28, WHITE, True)

    steps = [
        ("1", "KPI Cards",          "Total records, median salary,\ntop role, accuracy",    TEAL),
        ("2", "Market Charts",       "Distribution, experience,\ntop roles, remote trends", AMBER),
        ("3", "Prediction Studio",   "Fill the form, click Predict,\nget an instant result", CORAL),
        ("4", "Peer Comparison",     "How you compare to similar\nprofessionals in the data", VIOLET),
        ("5", "AI Insight",          "LLM-generated narrative\nfrom the API via Ollama",     SKY),
        ("6", "Prediction History",  "Past predictions read\nback from Supabase",            LIME),
    ]

    for i, (num, title, desc, color) in enumerate(steps):
        col = i % 3
        row = i // 3
        x = Inches(0.8 + col * 3.95)
        y = Inches(2.3 + row * 2.45)

        c = rect(slide, x, y, Inches(3.6), Inches(2.1), SURFACE, 0.06)
        add_entrance_anim(slide, c, i * 200, 400, "fade")
        # top accent
        line_shape(slide, x + Inches(0.1), y + Inches(0.08), Inches(3.4), Inches(0.04), color)
        # number circle
        nc = circle(slide, x + Inches(0.25), y + Inches(0.35), Inches(0.55), color)
        txt(slide, x + Inches(0.25), y + Inches(0.35), Inches(0.55), Inches(0.55),
            num, 20, DARK, True, PP_ALIGN.CENTER)
        txt(slide, x + Inches(1.0), y + Inches(0.35), Inches(2.3), Inches(0.4),
            title, 17, WHITE, True)
        txt(slide, x + Inches(1.0), y + Inches(0.8), Inches(2.3), Inches(1.0),
            desc, 13, MUTED)

    txt(slide, Inches(0.8), Inches(7.0), Inches(11), Inches(0.35),
        ">>  Switching to live dashboard now", 15, TEAL, True)


def slide_api(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    glow_circle(slide, Inches(11), Inches(-1), Inches(2.5), SKY, 93)
    deco_dots_left(slide)

    pill(slide, Inches(0.8), Inches(0.5), "API + CLIENT", SKY, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "GET /predict - one endpoint, full response", 28, WHITE, True)

    # left: request card
    c1 = rect(slide, Inches(0.8), Inches(2.3), Inches(5.7), Inches(4.6), SURFACE, 0.05)
    add_entrance_anim(slide, c1, 200, 500, "fade")
    line_shape(slide, Inches(0.8), Inches(2.38), Inches(5.7), Inches(0.04), SKY)

    multi(slide, Inches(1.1), Inches(2.55), Inches(5.2), Inches(4.2), [
        ("Request", 19, SKY, True),
        ("", 6, MUTED, False),
        ("GET /predict?experience_level=SE", 13, WHITE, False),
        ("  &employment_type=FT", 13, MUTED, False),
        ("  &job_title=Data Scientist", 13, MUTED, False),
        ("  &employee_residence=US", 13, MUTED, False),
        ("  &company_size=M&remote_ratio=100", 13, MUTED, False),
        ("", 8, MUTED, False),
        ("Response includes:", 15, WHITE, True),
        ("  predicted_salary_usd", 13, TEAL, False),
        ("  peer_context", 13, AMBER, False),
        ("  llm_analysis", 13, VIOLET, False),
    ])

    # right: client + error handling
    c2 = rect(slide, Inches(6.9), Inches(2.3), Inches(5.6), Inches(4.6), SURFACE, 0.05)
    add_entrance_anim(slide, c2, 400, 500, "fade")
    line_shape(slide, Inches(6.9), Inches(2.38), Inches(5.6), Inches(0.04), CORAL)

    multi(slide, Inches(7.2), Inches(2.55), Inches(5.0), Inches(4.2), [
        ("Client Script", 19, CORAL, True),
        ("", 6, MUTED, False),
        ("python predict_client.py", 14, WHITE, False),
        ("  --experience-level SE", 13, MUTED, False),
        ("  --job-title \"Data Scientist\"", 13, MUTED, False),
        ("  --remote-ratio 100", 13, MUTED, False),
        ("", 10, MUTED, False),
        ("Error handling:", 15, WHITE, True),
    ])

    errors = [
        ("Timeout", TEAL), ("Connection failure", AMBER),
        ("HTTP errors", CORAL), ("Invalid JSON", VIOLET),
    ]
    for i, (label, color) in enumerate(errors):
        y = Inches(5.3 + i * 0.4)
        circle(slide, Inches(7.5), y + Inches(0.05), Inches(0.18), color)
        txt(slide, Inches(7.85), y, Inches(3.0), Inches(0.35), label, 13, WHITE)


def slide_decisions(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    deco_corners(slide)

    pill(slide, Inches(0.8), Inches(0.5), "DECISIONS", PINK, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "Key tradeoffs I made and why", 28, WHITE, True)

    decisions = [
        (TEAL,   "LLM lives in the API, not the dashboard",
         "Pipeline stays local: predict > analyze > persist in one call. Dashboard only reads."),
        (AMBER,  "Static data stays in CSV, not Supabase",
         "600 unchanging records don't belong in a transactional database. Supabase stores dynamic data only."),
        (CORAL,  "Graceful degradation everywhere",
         "If Ollama or Supabase is unavailable, everything still works. No breaking, just a message."),
    ]

    for i, (color, title, body) in enumerate(decisions):
        y = Inches(2.3 + i * 1.65)
        c = rect(slide, Inches(0.8), y, Inches(11.5), Inches(1.4), SURFACE, 0.05)
        add_entrance_anim(slide, c, i * 300, 500, "fade")
        # left color bar
        line_shape(slide, Inches(0.8), y + Inches(0.1), Inches(0.06), Inches(1.2), color)
        # icon circle
        circle(slide, Inches(1.15), y + Inches(0.35), Inches(0.6), color, 75)
        txt(slide, Inches(1.15), y + Inches(0.35), Inches(0.6), Inches(0.6),
            str(i + 1), 20, color, True, PP_ALIGN.CENTER)
        # text
        txt(slide, Inches(2.0), y + Inches(0.2), Inches(10.0), Inches(0.4),
            title, 18, WHITE, True)
        txt(slide, Inches(2.0), y + Inches(0.7), Inches(10.0), Inches(0.55),
            body, 14, MUTED)


def slide_remote_chart(prs):
    """Bonus chart slide: remote vs on-site."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    glow_circle(slide, Inches(10), Inches(-1), Inches(3), CORAL, 94)
    glow_circle(slide, Inches(-1), Inches(5), Inches(2), TEAL, 95)

    pill(slide, Inches(0.8), Inches(0.5), "WORK STYLE", CORAL, DARK)
    txt(slide, Inches(0.8), Inches(1.15), Inches(11), Inches(0.7),
        "Remote work leads on median salary", 28, WHITE, True)

    # chart
    chart_data = CategoryChartData()
    chart_data.categories = ["On-site (0%)", "Hybrid (50%)", "Remote (100%)"]
    chart_data.add_series("Median Salary", [99000, 69999, 115000])

    cf = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.8), Inches(2.5), Inches(7.0), Inches(4.2),
        chart_data,
    )
    chart = cf.chart
    chart.has_legend = False
    plot = chart.plots[0]
    plot.gap_width = 120

    bar_colors = [AMBER, VIOLET, TEAL]
    series = plot.series[0]
    for idx in range(3):
        pt = series.points[idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = bar_colors[idx]

    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(12)
    dl.font.color.rgb = WHITE
    dl.font.bold = True
    dl.number_format = '$#,##0'
    dl.show_value = True

    add_entrance_anim(slide, cf, 300, 700, "fade")

    # right side insight cards
    insights = [
        ("381 records", "63% of all data\nis fully remote", TEAL),
        ("$115,000", "Remote workers earn\n16% above on-site", AMBER),
        ("Hybrid lowest", "$70K median -\nsmallest sample (99)", VIOLET),
    ]
    for i, (val, desc, color) in enumerate(insights):
        y = Inches(2.5 + i * 1.45)
        c = rect(slide, Inches(8.3), y, Inches(4.2), Inches(1.2), SURFACE, 0.05)
        add_entrance_anim(slide, c, 700 + i * 200, 400, "fade")
        line_shape(slide, Inches(8.3), y + Inches(0.08), Inches(0.06), Inches(1.05), color)
        txt(slide, Inches(8.65), y + Inches(0.15), Inches(3.5), Inches(0.35),
            val, 18, color, True)
        txt(slide, Inches(8.65), y + Inches(0.55), Inches(3.5), Inches(0.5),
            desc, 12, MUTED)


def slide_thank_you(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)

    # lots of decorative orbs
    glow_circle(slide, Inches(8), Inches(-2), Inches(5), TEAL, 92)
    glow_circle(slide, Inches(-2), Inches(3), Inches(4), CORAL, 93)
    glow_circle(slide, Inches(10), Inches(5), Inches(3), VIOLET, 94)
    glow_circle(slide, Inches(3), Inches(-1), Inches(2.5), AMBER, 95)
    glow_circle(slide, Inches(0), Inches(6), Inches(2), SKY, 95)
    add_decorative_dots(slide, Inches(10), Inches(1), 7, 12, Inches(0.22), TEAL, 90)
    add_decorative_dots(slide, Inches(0.5), Inches(5.5), 5, 5, Inches(0.22), CORAL, 91)

    # multi-color accent lines
    line_shape(slide, Inches(4.5), Inches(2.3), Inches(0.9), Inches(0.07), TEAL)
    line_shape(slide, Inches(5.5), Inches(2.3), Inches(0.9), Inches(0.07), CORAL)
    line_shape(slide, Inches(6.5), Inches(2.3), Inches(0.9), Inches(0.07), AMBER)
    line_shape(slide, Inches(7.5), Inches(2.3), Inches(0.9), Inches(0.07), VIOLET)

    t = txt(slide, Inches(1), Inches(2.6), Inches(11.3), Inches(1.2),
            "Thank You", 56, TEAL, True, PP_ALIGN.CENTER)
    add_entrance_anim(slide, t, 0, 800, "fade")

    q = txt(slide, Inches(1), Inches(3.8), Inches(11.3), Inches(0.7),
            "Questions?", 30, WHITE, False, PP_ALIGN.CENTER)
    add_entrance_anim(slide, q, 400, 600, "fade")

    txt(slide, Inches(1), Inches(4.8), Inches(11.3), Inches(0.5),
        "Yasser Hamdan", 20, MUTED, True, PP_ALIGN.CENTER)

    # live URL pill
    p = pill(slide, Inches(4.5), Inches(5.6), "Live Dashboard", TEAL, DARK, w=Inches(4.3))
    add_entrance_anim(slide, p, 800, 500, "fade")

    txt(slide, Inches(1), Inches(6.2), Inches(11.3), Inches(0.4),
        "week1-projectsalaryprediction-yvatd83p7jyt97qqowjo3j.streamlit.app", 12, MUTED, False, PP_ALIGN.CENTER)


# ── main ─────────────────────────────────────────────────────────────────

def main():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H

    slide_title(prs)         #  1 - Title
    slide_problem(prs)       #  2 - Problem
    slide_architecture(prs)  #  3 - Architecture
    slide_data_stats(prs)    #  4 - Data + Chart
    slide_model(prs)         #  5 - Model
    slide_top_roles(prs)     #  6 - Top Roles Chart
    slide_remote_chart(prs)  #  7 - Remote vs On-site Chart
    slide_demo(prs)          #  8 - Live Demo
    slide_api(prs)           #  9 - API + Client
    slide_decisions(prs)     # 10 - Decisions
    slide_thank_you(prs)     # 11 - Thank You

    path = "PayScope_Presentation_v2.pptx"
    prs.save(path)
    print(f"Saved {path} -- {len(prs.slides)} slides")


if __name__ == "__main__":
    main()
