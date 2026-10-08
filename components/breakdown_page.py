"""components/breakdown_page.py — one renderer for the Gender, Group Wise and Regular vs Private pages
(they share the same structure: KPIs, hero chart, trend, gap, share, heatmap, table)."""
import streamlit as st
from components.page_boot import boot, delta_kpi, years_note
from components.filter_bar import render_filter_row
from components.kpi_card import render_kpi_row, format_compact
from components.chart_card import chart_card
from charts.common import YEARS, prev_year, like_for_like, rate
from charts.page_charts import *  # noqa


def render_breakdown(page, subtitle, df, dim, values, hi, lo, key, icons):
    boot(page, subtitle)
    avail = sorted(df["Board"].unique())
    f = render_filter_row([
        {"label": "Year", "options": YEARS[::-1], "default": 2026, "key": f"{key}_year"},
        {"label": "Boards (only those publishing this data)", "options": avail, "default": [], "key": f"{key}_boards", "dropdown": True},
    ])
    year = f[f"{key}_year"] or 2026; boards = f[f"{key}_boards"] or avail
    other = prev_year(year)
    d = df[df["Board"].isin(boards)]
    cur = rate(d[d["Year"] == year], [dim]).set_index(dim)
    if cur.empty:
        st.warning(f"None of the selected boards published this breakdown for {year}."); return
    prv = None
    if other:
        ll = like_for_like(d, year, other)
        prv = rate(ll[ll["Year"] == other], [dim]).set_index(dim)
        cur_ll = rate(ll[ll["Year"] == year], [dim]).set_index(dim)
    kp = []
    for v, (ic, ac) in zip(values, icons):
        if v not in cur.index: continue
        txt, good = ("", True)
        if prv is not None and v in prv.index and v in cur_ll.index:
            txt, good = delta_kpi(cur_ll.loc[v, "Pass %"], prv.loc[v, "Pass %"], pct=True)
        kp.append(dict(icon=ic, value=f"{cur.loc[v,'Pass %']*100:.1f}%", label=f"{v} pass rate · {year}", delta=txt, delta_positive=good, accent=ac,
                       spark=[x for x in rate(d[d["Year"] == y], [dim]).set_index(dim)["Pass %"].reindex([v]).tolist() if x == x] if False else None))
    kp.append(dict(icon="groups", value=format_compact(cur["Appeared"].sum()), label=f"Appeared · {year}", accent="blue"))
    kp.append(dict(icon="account_balance", value=str(d[d["Year"] == year]["Board"].nunique()), label="Boards with data", accent="blue"))
    render_kpi_row(kp)
    years_note(year, other, "Boards that did not publish both years are excluded from the change figures.")

    with chart_card(f"Pass % by {dim}", f"By board, {year}"):
        st.plotly_chart(chart_dim_by_board(df, dim, boards, year), width="stretch")
    a, b = st.columns(2)
    with a:
        with chart_card(f"{dim} Trend", "Aggregate pass % across 2024-2026"):
            st.plotly_chart(chart_dim_trend(df, dim, boards), width="stretch")
    with b:
        with chart_card(f"Share of Candidates by {dim}", f"{year}"):
            st.plotly_chart(chart_dim_donut(df, dim, boards, year), width="stretch")
    a, b = st.columns(2)
    with a:
        with chart_card("Gap by Board" if hi else "Spread", f"{hi} vs {lo}, points" if hi else ""):
            if hi: st.plotly_chart(chart_dim_gap(df, dim, hi, lo, boards, year), width="stretch")
            else: st.plotly_chart(chart_dim_box(df, dim, boards, [y for y in YEARS]), width="stretch")
    with b:
        with chart_card("Candidate Mix by Board", f"{year}"):
            st.plotly_chart(chart_dim_share_by_board(df, dim, boards, year), width="stretch")
    a, b = st.columns(2)
    with a:
        with chart_card("Pass % Heatmap", f"Board x {dim}, {year}"):
            st.plotly_chart(chart_dim_heatmap(df, dim, boards, year), width="stretch")
    with b:
        with chart_card("Size and Performance", f"{year}"):
            st.plotly_chart(chart_dim_treemap(df, dim, boards, year), width="stretch")
    with chart_card("Data Table", f"{year}"):
        st.dataframe(dim_table(df, dim, boards, year), width="stretch", hide_index=True)