"""pages/2_Board_Comparison.py — compare boards on appeared / pass % across 2024-2026."""
import streamlit as st
from components.page_boot import boot
from components.filter_bar import render_filter_row
from components.chart_card import chart_card
from data.loader import load_overall_summary
from charts.common import YEARS
from charts.page_charts import *  # noqa

boot("Board Comparison", "Compare all 15 boards side by side across 2024, 2025 and 2026.")
ov = load_overall_summary()
f = render_filter_row([
    {"label": "Years", "options": YEARS, "default": YEARS, "key": "bc_years", "multi": True},
    {"label": "Ranking year", "options": YEARS[::-1], "default": 2026, "key": "bc_year"},
    {"label": "Boards", "options": sorted(ov["Board"].unique()), "default": [], "key": "bc_boards", "dropdown": True},
])
years = sorted(f["bc_years"] or YEARS); year = f["bc_year"] or 2026
ov = ov[ov["Board"].isin(f["bc_boards"] or ov["Board"].unique())]
with chart_card("Pass % by Board", "Grouped by year, sorted by average pass rate"):
    st.plotly_chart(chart_pass_rate_by_board(ov, years), width="stretch")
with chart_card("Candidates Appeared by Board"):
    st.plotly_chart(chart_appeared_by_board(ov, years), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Board Ranking", f"Pass %, {year}"):
        st.plotly_chart(chart_board_ranking(ov, year), width="stretch")
with b:
    with chart_card("Passed vs Failed", f"{year}"):
        st.plotly_chart(chart_passed_vs_failed(ov, year), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Size vs Performance", f"Bubble = candidates, {year}"):
        st.plotly_chart(chart_size_vs_performance(ov, year), width="stretch")
with b:
    with chart_card("Pass % Heatmap", "Board x year"):
        st.plotly_chart(chart_board_year_heatmap(ov), width="stretch")
with chart_card("Comparison Table"):
    st.dataframe(comparison_table(ov, years), width="stretch", hide_index=True)