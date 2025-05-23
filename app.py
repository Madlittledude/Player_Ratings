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

# ─────────────────────────────────────────────────────────────
# 1. LOAD PLAYER INFO FROM JSON
# ─────────────────────────────────────────────────────────────
with open("Player_Info.json", "r") as f:
    PLAYER_INFO = json.load(f)

# ─────────────────────────────────────────────────────────────
# 2. HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def category_average(sub_scores: dict[str, int]) -> float:
    """Return the mean of a dict of sub-skill scores."""
    return stats.mean(sub_scores.values())

def build_barograph(
    scores: dict[str, dict[str, int]],
    show_sub: bool,
    show_avg: bool
) -> go.Figure:
    """
    Create a layered Plotly bar chart.
    - Thin colored bars for each sub-skill
    - Translucent wide bar for the category average
    """
    fig = go.Figure()
    categories = list(scores.keys())
    palette = ["#636EFA", "#EF553B", "#00CC96"]

    # Sub-skill bars
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

    # Category-average bars
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
        yaxis=dict(title="Score (1–120)"),
        legend_title="Legend",
        template="plotly_white"
    )
    return fig

def create_docx_report(
    player_name: str,
    player_type: str,
    scores: dict[str, dict[str, int]]
) -> bytes:
    """
    Build and return a .docx report with:
      - Header
      - Timestamp
      - Embedded bar chart PNG
      - Category averages list
      - Overall rating
    """
    # Generate chart image
    fig = build_barograph(scores, show_sub=True, show_avg=True)
    img = fig.to_image(format="png", width=800, height=400)

    doc = Document()
    doc.add_heading(f"{player_name} – {player_type} Stats Report", level=1)
    doc.add_paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    doc.add_picture(io.BytesIO(img), width=Inches(6))
    doc.add_paragraph()

    # Category averages
    for cat, subdict in scores.items():
        avg = category_average(subdict)
        doc.add_paragraph(f"• {cat}: {avg:.1f}", style="List Bullet")

    overall = stats.mean(category_average(subdict) for subdict in scores.values())
    doc.add_paragraph()
    doc.add_paragraph(f"Overall Rating: {overall:.1f} / 120", style="Intense Quote")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────
# 3. STREAMLIT APP
# ─────────────────────────────────────────────────────────────
def main():
    st.title("🏅 Player Stats: Barograph")
    st.markdown("Select a player, upload a previous report (optional), then rate skills and export a new version!")

    # Player selection
    player_type = st.selectbox("Player Type", list(PLAYER_INFO.keys()))
    player_name = st.selectbox(
        "Player Name",
        list(PLAYER_INFO[player_type]["Players"].keys())
    )

    # Optional upload of existing report
    uploaded = st.file_uploader("Upload existing .docx report", type="docx")
    parsed_avgs: dict[str, float] = {}
    if uploaded:
        doc = Document(uploaded)
        for para in doc.paragraphs:
            text = para.text.strip()
            if text.startswith("• "):
                parts = text[2:].split(":")
                if len(parts) == 2:
                    cat, val = parts
                    try:
                        parsed_avgs[cat.strip()] = float(val)
                    except ValueError:
                        pass

    st.header(f"{player_name} – {player_type} Skills")

    # Build scores (prefilled if report uploaded)
    scores: dict[str, dict[str, int]] = {}
    skillset = PLAYER_INFO[player_type]["Skillset"]
    for cat, subs in skillset.items():
        with st.expander(cat, expanded=True):
            scores[cat] = {}
            default = int(parsed_avgs.get(cat, 100))
            for sub in subs:
                scores[cat][sub] = st.slider(
                    label=sub,
                    min_value=1,
                    max_value=100,
                    value=default,
                    key=f"{cat}_{sub}"
                )

    # Specialty sliders (if any)
    specialty = PLAYER_INFO[player_type]["Players"][player_name].get("Specialty", {})
    for spec_cat, subs in specialty.items():
        with st.expander(f"Specialty: {spec_cat}", expanded=True):
            scores[spec_cat] = {}
            default = int(parsed_avgs.get(spec_cat, 100))
            for sub in subs:
                scores[spec_cat][sub] = st.slider(
                    label=sub,
                    min_value=1,
                    max_value=100,
                    value=default,
                    key=f"{spec_cat}_{sub}"
                )

    # Toggles
    col1, col2 = st.columns(2)
    show_sub = col1.checkbox("Show Sub-skill Bars", True)
    show_avg = col2.checkbox("Show Category Average Bars", True)

    # Render chart
    fig = build_barograph(scores, show_sub, show_avg)
    st.plotly_chart(fig, use_container_width=True)

    # Numeric breakdown
    st.markdown("### Category Averages")
    for cat, subdict in scores.items():
        st.write(f"**{cat}**: {category_average(subdict):.1f}")

    overall = stats.mean(category_average(v) for v in scores.values())
    st.markdown(f"**Overall Rating:** {overall:.1f} / 120")

    # Export DOCX with date in filename
    if st.button("Save Report as DOCX"):
        docx_bytes = create_docx_report(player_name, player_type, scores)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{player_name.replace(' ','_')}_{player_type}_Report.docx"
        st.download_button(
            "Download Report",
            data=docx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

if __name__ == "__main__":
    main()
