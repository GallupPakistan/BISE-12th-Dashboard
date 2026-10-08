"""pages/6_Subject_Wise.py — subject pass rates (Part-II / final-year papers) across boards."""
import streamlit as st
from components.page_boot import boot, years_note
from components.filter_bar import render_filter_row
from components.kpi_card import render_kpi_row
from components.chart_card import chart_card
from data.loader import load_subject_table
from charts.common import YEARS, prev_year, rate
from charts.page_charts import *  # noqa

boot("Subject Wise", "Subject-level pass rates for boards that publish them, 2024-2026.")
df = load_subject_table()
avail = sorted(df["Board"].unique())
f = render_filter_row([
    {"label": "Year", "options": YEARS[::-1], "default": 2026, "key": "sub_year"},
    {"label": "Boards (only those publishing subjects)", "options": avail, "default": [], "key": "sub_boards", "dropdown": True},
])
year = f["sub_year"] or 2026; boards = f["sub_boards"] or avail
s = subject_table(df, boards, year)
if s.empty:
    st.warning(f"None of the selected boards published subject results for {year}."); st.stop()
render_kpi_row([
    dict(icon="menu_book", value=str(len(s)), label=f"Subjects · {year}", accent="blue"),
    dict(icon="trending_up", value=f"{s.iloc[0]['Pass %']:.1f}%", label=f"Best: {s.iloc[0]['Subject']}", accent="green"),
    dict(icon="trending_down", value=f"{s.iloc[-1]['Pass %']:.1f}%", label=f"Lowest: {s.iloc[-1]['Subject']}", accent="red"),
    dict(icon="account_balance", value=str(df[(df['Board'].isin(boards)) & (df['Year'] == year)]['Board'].nunique()), label="Boards with data", accent="gold"),
])
st.caption("Subjects with fewer than 30 candidates are hidden. Boards name subjects differently, so identical subjects may appear more than once.")
a, b = st.columns(2)
with a:
    with chart_card("Highest and Lowest Pass Rates", f"{year}"):
        st.plotly_chart(chart_subject_best_worst(df, boards, year), width="stretch")
with b:
    with chart_card("Subject x Board Heatmap", "Most-attempted subjects"):
        st.plotly_chart(chart_subject_heatmap(df, boards, year), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Candidates vs Pass %", "Each dot is a subject"):
        st.plotly_chart(chart_subject_scatter(df, boards, year), width="stretch")
with b:
    with chart_card("Subject Trend", "Most-attempted subjects, 2024-2026"):
        st.plotly_chart(chart_subject_trend(df, boards), width="stretch")
with chart_card("Subject Size and Performance", f"{year}"):
    st.plotly_chart(chart_subject_treemap(df, boards, year), width="stretch")
with chart_card("Data Table", f"{year}"):
    st.dataframe(s, width="stretch", hide_index=True)