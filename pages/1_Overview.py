"""pages/1_Overview.py — province-wide top-line view for 2024-2026 across 15 BISE boards."""
import streamlit as st
from components.page_boot import boot, delta_kpi, years_note
from components.filter_bar import render_filter_bar
from components.kpi_card import render_kpi_row, format_compact
from components.chart_card import chart_card
from components.page_header import render_page_header
from components.provincial_tiles import render_province_tiles
from components.top_boards import render_top_boards
from data.loader import load_overall_summary, load_gender_table, load_category_table
from data.availability import PROVINCE_BOARD_MAP
from charts.common import YEARS, prev_year, like_for_like
from charts.overview_charts import *  # noqa

boot("Overview", "Province-wide 12th Class (HSSC) results, 2024 vs 2025 vs 2026, across all 15 BISE boards.")

year = render_page_header("Select Year to View Results", year_options=[2026, 2025, 2024], year_default=2026,
                          key="overview_year_selector")
other = prev_year(year)

ALL = "All Provinces"
prov = render_filter_bar("Province", [ALL] + list(PROVINCE_BOARD_MAP), default=ALL, key="overview_province_filter") or ALL

ov = load_overall_summary()
boards = [b for bs in PROVINCE_BOARD_MAP.values() for b in bs] if prov == ALL else PROVINCE_BOARD_MAP[prov]
df = ov[ov["Board"].isin(boards)]
gdf = load_gender_table(); gdf = gdf[gdf["Board"].isin(boards)]
cdf = load_category_table(); cdf = cdf[cdf["Board"].isin(boards)]

tot = compute_province_totals(df)
cur = tot[year]
cur_pct = cur["passed"] / cur["appeared"] if cur["appeared"] else 0

ll = like_for_like(df, year, other) if other else df.iloc[0:0]
def _sum(y, c): return int(ll[ll["Year"] == y][c].sum()) if other else 0
if other:
    ca, cp, pa, pp = _sum(year, "Appeared"), _sum(year, "Passed"), _sum(other, "Appeared"), _sum(other, "Passed")
    d_app = delta_kpi(ca, pa); d_pas = delta_kpi(cp, pp); d_fail = delta_kpi(ca - cp, pa - pp, invert=True)
    d_pct = delta_kpi(cp / ca if ca else 0, pp / pa if pa else 0, pct=True)
else:
    d_app = d_pas = d_fail = d_pct = ("", True)

def spark(key): return [tot[y][key] for y in YEARS if tot[y]["appeared"]]
render_kpi_row([
    dict(icon="groups", value=format_compact(cur["appeared"]), label=f"Appeared · {year}", delta=d_app[0], delta_positive=d_app[1], accent="blue", spark=spark("appeared")),
    dict(icon="check_circle", value=format_compact(cur["passed"]), label=f"Passed · {year}", delta=d_pas[0], delta_positive=d_pas[1], accent="green", spark=spark("passed")),
    dict(icon="cancel", value=format_compact(cur["failed"]), label=f"Failed · {year}", delta=d_fail[0], delta_positive=d_fail[1], accent="red", spark=spark("failed")),
    dict(icon="percent", value=f"{cur_pct*100:.1f}%", label=f"Pass Rate · {year}", delta=d_pct[0], delta_positive=d_pct[1], accent="gold",
         spark=[tot[y]["passed"] / tot[y]["appeared"] for y in YEARS if tot[y]["appeared"]]),
    dict(icon="account_balance", value=str(cur["boards"]), label=f"Boards reporting · {year}", accent="blue"),
])
years_note(year, other, "Totals show every board that published that year.")

gain, loss = top_movers(df, year, other) if other else (None, None)
if gain:
    c1, c2 = st.columns(2)
    c1.success(f"**Top gainer:** {gain[0]}  ({gain[1]*100:+.1f} pts vs {other})")
    c2.error(f"**Top decliner:** {loss[0]}  ({loss[1]*100:+.1f} pts vs {other})")

left, right = st.columns([1.6, 1])
with left:
    with chart_card("Pakistan Map", f"Appeared by province, {year}. Hover for all years."):
        st.plotly_chart(chart_pakistan_map(ov, year), width="stretch")
with right:
    with chart_card("Top 3 Boards by Pass %", "Highest pass rate in each year"):
        render_top_boards(df, n=3, years=(2026, 2025, 2024))

with chart_card("Province Snapshot", f"{year}"):
    metric = st.pills("Metric", ["Appeared", "Pass %"], default="Appeared", key="ov_tile_metric", label_visibility="collapsed") or "Appeared"
    render_province_tiles(df, metric, year)

a, b = st.columns(2)
with a:
    with chart_card("Overall Performance", "Appeared vs Passed vs Failed"):
        st.plotly_chart(chart_yoy_totals(df), width="stretch")
with b:
    with chart_card("Pass % Trend by Province", "Aggregate pass rate, 2024-2026"):
        st.plotly_chart(chart_province_pass_trend(df), width="stretch")

a, b = st.columns(2)
with a:
    with chart_card("Board Pass Rate", f"{year}"):
        st.plotly_chart(chart_board_pass_rate(df, year), width="stretch")
with b:
    with chart_card("Pass % Change by Board", f"{year} vs {other}" if other else "Needs an earlier year"):
        if other: st.plotly_chart(chart_yoy_change_by_board(df, year, other), width="stretch")
        else: st.info("2024 is the first year in the dataset.")

a, b = st.columns(2)
with a:
    with chart_card("Pass % Across Years by Board", "Boards with at least two years of data"):
        st.plotly_chart(chart_trend_lines(df), width="stretch")
with b:
    with chart_card("Share of Candidates by Board", f"Appeared, {year}"):
        st.plotly_chart(chart_appeared_share(df, year), width="stretch")

a, b = st.columns(2)
with a:
    with chart_card("Gender: Pass Rate", "Male vs Female, boards that publish gender data"):
        st.plotly_chart(chart_gender_pass_rate(gdf), width="stretch")
with b:
    with chart_card("Gender: Share of Candidates", f"{year}"):
        st.plotly_chart(chart_gender_share(gdf, year), width="stretch")
a, b = st.columns(2)
with a:
    with chart_card("Regular vs Private: Pass Rate", "Boards that publish category data"):
        st.plotly_chart(chart_category_pass_rate(cdf), width="stretch")
with b:
    with chart_card("Regular vs Private: Share", f"{year}"):
        st.plotly_chart(chart_category_share(cdf, year), width="stretch")