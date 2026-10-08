"""pages/7_District_Wise.py — district results for boards that publish them."""
import streamlit as st
from components.page_boot import boot
from components.filter_bar import render_filter_row
from components.kpi_card import render_kpi_row, format_compact
from components.chart_card import chart_card
from data.loader import load_district_table
from charts.common import YEARS, rate
from charts.page_charts import *  # noqa

boot("District Wise", "District-level results for the boards that publish them.", stat_label="Boards with districts", stat_value="8", stat_icon="map")
df = load_district_table()
avail = sorted(df["Board"].unique())
f = render_filter_row([
    {"label": "Board", "options": avail, "default": "DGK" if "DGK" in avail else avail[0], "key": "dist_board"},
    {"label": "Year", "options": YEARS[::-1], "default": 2026, "key": "dist_year"},
])
board = f["dist_board"] or "DGK"; year = f["dist_year"] or 2026
sub = df[df["Board"] == board]
have = sorted(sub["Year"].unique())
if year not in have:
    st.info(f"{board} publishes district data for {', '.join(map(str, have))} only, so {max(have)} is shown instead of {year}.")
    year = max(have)
t = district_table(df, board, year)
render_kpi_row([
    dict(icon="map", value=str(len(t)), label=f"Districts · {board}", accent="blue"),
    dict(icon="groups", value=format_compact(t["Appeared"].sum()), label=f"Appeared · {year}", accent="blue"),
    dict(icon="trending_up", value=f"{t.iloc[0]['Pass %']:.1f}%", label=f"Best: {t.iloc[0]['District']}", accent="green"),
    dict(icon="trending_down", value=f"{t.iloc[-1]['Pass %']:.1f}%", label=f"Lowest: {t.iloc[-1]['District']}", accent="red"),
])
st.caption("Years available for " + board + ": " + ", ".join(map(str, have)) + ".")
with chart_card("Pass % by District", "Grouped by year"):
    st.plotly_chart(chart_district_rate(df, board, have), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Candidates by District"):
        st.plotly_chart(chart_district_appeared(df, board, have), width="stretch")
with b:
    with chart_card("Passed vs Failed", f"{year}"):
        st.plotly_chart(chart_district_pass_fail(df, board, year), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Size vs Performance", f"{year}"):
        st.plotly_chart(chart_district_scatter(df, board, year), width="stretch")
with b:
    with chart_card("District Share", f"{year}"):
        st.plotly_chart(chart_district_treemap(df, board, year), width="stretch")
with chart_card("District Trend"):
    st.plotly_chart(chart_district_trend(df, board), width="stretch")
with chart_card("Data Table", f"{board} {year}"):
    st.dataframe(t, width="stretch", hide_index=True)
