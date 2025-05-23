# player_barograph_streamlit.py
# Run with: streamlit run player_barograph_streamlit.py

import io
import json
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import statistics as stats
from docx import Document
from docx.shared import Inches
import re
import random

# ─────────────────────────────────────────────────────────────
# 1. LOAD PLAYER INFO FROM JSON
# ─────────────────────────────────────────────────────────────
with open("Player_Info.json", "r") as f:
    PLAYER_INFO = json.load(f)

# ─────────────────────────────────────────────────────────────
# 2. HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def category_average(sub_scores: dict[str, int]) -> float:
    capped_scores = [min(100, v) for v in sub_scores.values()]
    return stats.mean(capped_scores)

def build_barograph(scores: dict[str, dict[str, int]], show_sub: bool, show_avg: bool) -> go.Figure:
    fig = go.Figure()
    categories = list(scores.keys())
    palette = ["#636EFA", "#EF553B", "#00CC96"]

    if show_sub:
        for i, cat in enumerate(categories):
            for j, sub in enumerate(scores[cat]):
                fig.add_trace(go.Bar(
                    x=[i + (j - 1) * 0.22],
                    y=[scores[cat][sub]],
                    width=0.2,
                    name=sub,
                    marker_color=palette[j % len(palette)],
                    legendgroup=sub,
                    showlegend=(i == 0),
                ))

    if show_avg:
        for i, cat in enumerate(categories):
            avg = category_average(scores[cat])
            fig.add_trace(go.Bar(
                x=[i],
                y=[avg],
                width=0.6,
                marker=dict(color="rgba(128,128,128,0.35)"),
                name=f"{cat} Avg",
                legendgroup="avg",
                showlegend=(i == 0),
            ))

    fig.update_layout(
        barmode="overlay",
        title="Skill Barograph",
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(categories))),
            ticktext=categories,
            title="Skill Category"
        ),
        yaxis=dict(title="Score (1–100)"),
        legend_title="Legend",
        template="plotly_white"
    )
    return fig

def parse_docx_report(docx_file):
    doc = Document(docx_file)
    meta = {"player_type": None, "player_name": None, "category_history": {}, "overall_history": []}
    cat_pattern = re.compile(r"^\u2022\s*([^:]+):\s*(.+)$")
    overall_header_seen = False
    for para in doc.paragraphs:
        text = para.text.strip()
        if text.endswith("Stats Report") and "–" in text:
            p, t = text.replace("Stats Report", "").split("–")
            meta["player_name"] = p.strip()
            meta["player_type"] = t.strip()
        elif cat_pattern.match(text):
            m = cat_pattern.match(text)
            cat = m.group(1).strip()
            vals = [float(x.strip()) for x in m.group(2).split(";") if x.strip()]
            meta["category_history"][cat] = vals
        elif text == "Overall Ratings by Date:":
            overall_header_seen = True
        elif overall_header_seen and re.match(r"^\d{4}-\d{2}-\d{2}:", text):
            date_part, val_part = text.split(":")
            meta["overall_history"].append((date_part.strip(), float(val_part.strip())))
        elif text.startswith("Overall Rating:"):
            pass
        elif text == "":
            overall_header_seen = False
    return meta

def create_docx_report(player_name: str, player_type: str, scores: dict[str, dict[str, int]], prev_cat_history: dict = None, prev_overall_history: list = None) -> bytes:
    cat_history = prev_cat_history.copy() if prev_cat_history else {}
    for cat, subdict in scores.items():
        avg = category_average(subdict)
        if cat not in cat_history:
            cat_history[cat] = []
        cat_history[cat].append(round(avg, 1))

    overall_score = round(stats.mean(category_average(subdict) for subdict in scores.values()), 1)
    overall_history = prev_overall_history.copy() if prev_overall_history else []
    today = datetime.now().strftime("%Y-%m-%d")
    overall_history.append((today, overall_score))

    fig = build_barograph(scores, show_sub=True, show_avg=True)
    img = fig.to_image(format="png", width=800, height=400)

    doc = Document()
    doc.add_heading(f"{player_name} – {player_type} Stats Report", level=1)
    doc.add_paragraph(f"Report Generated: {today} {datetime.now().strftime('%H:%M:%S')}")
    doc.add_picture(io.BytesIO(img), width=Inches(6))
    doc.add_paragraph()

    for cat in scores.keys():
        vals = cat_history[cat]
        vals_str = "; ".join([f"{v:.1f}" for v in vals])
        doc.add_paragraph(f"• {cat}: {vals_str}", style="List Bullet")

    doc.add_paragraph()
    doc.add_paragraph(f"Overall Rating: {overall_score:.1f} / 100", style="Intense Quote")
    doc.add_paragraph("-" * 38)
    doc.add_paragraph("Overall Ratings by Date:")
    for date_str, val in overall_history:
        doc.add_paragraph(f"{date_str}: {val:.1f}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
