"""pages/8_Grade_Distribution.py — A+ to E distribution of PASSED candidates."""
import streamlit as st
from components.page_boot import boot
from components.filter_bar import render_filter_row
from components.kpi_card import render_kpi_row, format_compact
from components.chart_card import chart_card
from data.loader import load_grade_table
from charts.common import YEARS
from charts.page_charts import *  # noqa

boot("Grade Distribution", "How passed candidates are spread across grades A+ to E.", stat_label="Boards with grades", stat_value="11", stat_icon="military_tech")
df = load_grade_table()
avail = sorted(df["Board"].unique())
f = render_filter_row([
    {"label": "Year", "options": YEARS[::-1], "default": 2026, "key": "gr_year"},
    {"label": "Boards (only those publishing grades)", "options": avail, "default": [], "key": "gr_boards", "dropdown": True},
])
year = f["gr_year"] or 2026; boards = f["gr_boards"] or avail
d = df[(df["Board"].isin(boards)) & (df["Year"] == year)]
if d.empty:
    st.warning(f"None of the selected boards published grades for {year}."); st.stop()
tot = d.groupby("Grade")["Count"].sum(); allg = tot.sum()
render_kpi_row([
    dict(icon="military_tech", value=f"{tot.get('A+',0)/allg*100:.1f}%", label=f"A+ share · {year}", accent="gold"),
    dict(icon="grade", value=f"{(tot.get('A+',0)+tot.get('A',0))/allg*100:.1f}%", label="A+ and A share", accent="blue"),
    dict(icon="warning", value=f"{(tot.get('D',0)+tot.get('E',0))/allg*100:.1f}%", label="D and E share", accent="red"),
    dict(icon="groups", value=format_compact(allg), label="Passed candidates graded", accent="green"),
])
st.caption("Grades describe passed candidates only. Boards label the top grade A+, A-1 or A1; all are shown as A+. Boards that publish no grade breakdown are not listed.")
a, b = st.columns(2)
with a:
    with chart_card("Grade Mix by Board", f"Share of passed candidates, {year}"):
        st.plotly_chart(chart_grade_stacked(df, boards, year), width="stretch")
with b:
    with chart_card("Overall Grade Share", f"{year}"):
        st.plotly_chart(chart_grade_donut(df, boards, year), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Grade Heatmap", f"Board x grade, {year}"):
        st.plotly_chart(chart_grade_heatmap(df, boards, year), width="stretch")
with b:
    with chart_card("Grade Mix by Year", "Selected boards"):
        st.plotly_chart(chart_grade_year_mix(df, boards), width="stretch")
with chart_card("A+ Share by Board", "Across years"):
    st.plotly_chart(chart_top_grade_share(df, boards, YEARS), width="stretch")
with chart_card("Data Table", f"{year}"):
    st.dataframe(grade_table(df, boards, year), width="stretch", hide_index=True)