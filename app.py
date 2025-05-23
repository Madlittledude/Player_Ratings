# player_barograph_streamlit.py
# Run with: streamlit run player_barograph_streamlit.py

import io
import streamlit as st
import plotly.graph_objects as go
import statistics as stats
from docx import Document
from docx.shared import Inches

# ─────────────────────────────────────────────────────────────
# 1. DEFINE YOUR SKILL TAXONOMY (at the top)
# ─────────────────────────────────────────────────────────────
# PLAYER_SKILLSETS = {
#     "Paralegal": {
#         "Execution":     ["Follow-through", "Accuracy", "Efficiency"],
#         "Judgment":      ["Prioritization", "Legal Discernment", "Escalation Timing"],
#         "Communication": ["Client Updates", "Internal Sync", "Written Clarity"],
#         "Organization":  ["Calendar Control", "File Order", "Tool Fluency"],
#         "Knowledge":     ["Procedure & Rules", "PI & Medical Concepts", "Research Savvy"],
#         "Initiative":    ["Case Vision", "Problem-Solving", "Professionalism"],
#     }
# }

# ─────────────────────────────────────────────────────────────
# 2. HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def category_average(sub_scores: dict[str, int]) -> float:
    """
    INPUT:
        sub_scores: dict of sub-skill → integer score
    OUTPUT:
        float average of the values
    """
    return stats.mean(sub_scores.values())


def build_barograph(
    scores: dict[str, dict[str, int]],
    show_sub: bool,
    show_avg: bool
) -> go.Figure:
    """
    INPUT:
        scores  → {category: {subskill: score}}
        show_sub → whether to draw sub-skill bars
        show_avg → whether to draw category-average bars
    OUTPUT:
        Plotly Figure with layered bars
    """
    fig = go.Figure()
    categories = list(scores.keys())
    x_positions = list(range(len(categories)))
    palette = ["#636EFA", "#EF553B", "#00CC96"]  # distinct colors for trio

    # -- sub-skill bars
    if show_sub:
        for idx, cat in enumerate(categories):
            subs = list(scores[cat].keys())
            for j, sub in enumerate(subs):
                fig.add_trace(go.Bar(
                    x=[idx + (j - 1) * 0.22],  # offsets: -0.22, 0, +0.22
                    y=[scores[cat][sub]],
                    width=0.2,
                    name=sub,
                    marker_color=palette[j],
                    legendgroup=sub,
                    showlegend=(idx == 0),
                ))

    # -- category-average bars
    if show_avg:
        for idx, cat in enumerate(categories):
            avg = category_average(scores[cat])
            fig.add_trace(go.Bar(
                x=[idx],
                y=[avg],
                width=0.6,
                marker=dict(color="rgba(128,128,128,0.35)"),
                name=f"{cat} Avg",
                legendgroup="avg",
                showlegend=(idx == 0),
            ))

    fig.update_layout(
        barmode="overlay",
        title="Skill Barograph",
        xaxis=dict(
            tickmode="array",
            tickvals=x_positions,
            ticktext=categories,
            title="Skill Category"
        ),
        yaxis=dict(title="Score (1–120)"),
        legend_title_text="Sub-skills & Averages",
        template="plotly_white"
    )
    return fig


def create_docx_report(
    player_name: str,
    player_type: str,
    scores: dict[str, dict[str, int]]
) -> bytes:
    """
    INPUT:
        player_name: Name of the player
        player_type: Type (e.g., Paralegal)
        scores: {category: {subskill: score}}
    OUTPUT:
        bytes of the DOCX file
    """
    # build the chart for embedding
    fig = build_barograph(scores, show_sub=True, show_avg=True)
    img_bytes = fig.to_image(format="png", width=800, height=400)

    doc = Document()
    doc.add_heading(f"{player_name} – {player_type} Stats Report", level=1)

    # insert chart
    image_stream = io.BytesIO(img_bytes)
    doc.add_picture(image_stream, width=Inches(6))

    doc.add_paragraph()

    # category averages
    for cat, subdict in scores.items():
        avg = category_average(subdict)
        doc.add_paragraph(f"• {cat}: {avg:.1f}", style="List Bullet")

    overall = stats.mean([category_average(subdict) for subdict in scores.values()])
    doc.add_paragraph()
    doc.add_paragraph(f"Overall Rating: {overall:.1f} / 100", style="Intense Quote")

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


# ─────────────────────────────────────────────────────────────
# 3. STREAMLIT APP
# ─────────────────────────────────────────────────────────────
def main():
    st.title("🏅 Player Stats: Barograph")
    st.markdown("Rate your team members and export a report!")

    # -- player info inputs
    player_type = st.selectbox("Player Type", list(PLAYER_SKILLSETS.keys()))
    player_name = st.text_input("Player Name", value="Enter name here")

    st.header(f"{player_name} – {player_type} Skills")

    # -- input scores
    scores: dict[str, dict[str, int]] = {}
    for cat, subs in PLAYER_SKILLSETS[player_type].items():
        with st.expander(cat, expanded=True):
            scores[cat] = {}
            for sub in subs:
                scores[cat][sub] = st.number_input(
                    label=sub,
                    min_value=1,
                    max_value=120,
                    value=100,
                    step=1,
                    key=f"{cat}_{sub}"
                )

    # -- toggles
    col1, col2 = st.columns(2)
    show_sub = col1.checkbox("Show Sub-skill Bars", value=True)
    show_avg = col2.checkbox("Show Category Average Bars", value=True)

    # -- render chart
    fig = build_barograph(scores, show_sub, show_avg)
    st.plotly_chart(fig, use_container_width=True)

    # -- display scores
    st.markdown("### Category Averages")
    for cat, subdict in scores.items():
        avg = category_average(subdict)
        st.write(f"**{cat}**: {avg:.1f}")

    overall = stats.mean([category_average(subdict) for subdict in scores.values()])
    st.markdown(f"**Overall Rating:** {overall:.1f} / 100")

    # -- export report
    if st.button("Save Report as DOCX"):
        docx_bytes = create_docx_report(player_name, player_type, scores)
        st.download_button(
            "Download Report",
            data=docx_bytes,
            file_name=f"{player_name.replace(' ', '_')}_{player_type}_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

if __name__ == "__main__":
    main()
