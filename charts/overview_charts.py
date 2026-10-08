"""
charts/overview_charts.py

Charts for pages/1_Overview.py.

Two families of functions live here:

1. Overall-Summary charts (chart_yoy_totals, chart_board_pass_rate,
   chart_yoy_change_by_board, chart_appeared_share, top_movers) — each
   takes the filtered "Overall Summary" DataFrame (already narrowed to
   the selected province's boards by the page file) and returns a
   plotly Figure. The "Overall Summary" sheet has 3 rows per board:
   Year=2025, Year=2026, and Year="Change (2026-2025)". Every function
   must exclude the "Change" rows before aggregating numeric totals —
   it is a delta row, not a data point — except
   chart_yoy_change_by_board() and top_movers(), which read it directly
   since it IS the change.

2. Gender / Regular-vs-Private aggregate charts (chart_gender_*,
   chart_category_*) — each takes the corresponding normalized table
   from data/recipes.py (already narrowed to the selected province's
   boards by the page file). Pass % is always recomputed as
   Passed / Appeared from the recipe tables' raw counts.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from data.availability import PROVINCE_BOARD_MAP


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Returns only the real Year=2025 / Year=2026 rows, dropping the
    'Change (2026-2025)' delta rows that the master sheet also carries."""
    return df[df["Year"].isin([2024, 2025, 2026])].copy()


def _base_layout(fig: go.Figure, legend_title: str = "", height: int = 400) -> go.Figure:
    """Shared layout for every Overview chart. The fixed height keeps
    the 2-column chart grid visually even; uniformtext hides (instead
    of overlapping) any bar/slice label that doesn't fit."""
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=COLORS["text_on_light"],
        font_size=13,
        legend_title_text=legend_title,
        margin=dict(t=10, b=10, l=10, r=10),
        height=height,
        uniformtext_mode=False,
        bargap=0.35,
    )
    fig.update_traces(textfont_size=14, constraintext="none", selector=dict(type="bar"))   # larger bar value labels
    fig.update_xaxes(gridcolor="rgba(20,27,60,0.08)")
    fig.update_yaxes(gridcolor="rgba(20,27,60,0.08)")
    return fig


from charts.common import (YEARS, YEAR_COLORS, GENDER_COLORS, CATEGORY_COLORS, compact as _compact,
                           rate, like_for_like, prev_year, grouped_year_bar, donut, empty_fig)


def compute_province_totals(df: pd.DataFrame) -> dict:
    """{year: {appeared, passed, failed}} for the boards in df, every year."""
    out = {}
    for y in YEARS:
        r = df[df["Year"] == y]
        a, p = int(r["Appeared"].sum()), int(r["Passed"].sum())
        out[y] = {"appeared": a, "passed": p, "failed": a - p, "boards": r["Board"].nunique()}
    return out


def chart_yoy_totals(df: pd.DataFrame) -> go.Figure:
    """Overall Performance (grouped bar): Appeared / Passed / Failed per year."""
    agg = df.groupby("Year")[["Appeared", "Passed"]].sum().reset_index()
    agg["Failed"] = agg["Appeared"] - agg["Passed"]
    fig = go.Figure()
    for metric, ck in (("Appeared", "accent"), ("Passed", "positive"), ("Failed", "negative")):
        fig.add_trace(go.Bar(x=agg["Year"].astype(str), y=agg[metric], name=metric, marker_color=COLORS[ck],
                             text=[_compact(v) for v in agg[metric]], textposition="outside", cliponaxis=False))
    fig.update_yaxes(tickformat="~s")
    return _base_layout(fig)


def chart_province_pass_trend(overall_df: pd.DataFrame) -> go.Figure:
    recs = []
    for province, boards in PROVINCE_BOARD_MAP.items():
        sub = overall_df[overall_df["Board"].isin(boards)]
        for y in YEARS:
            r = sub[sub["Year"] == y]
            if r["Appeared"].sum() == 0: continue
            recs.append({"Province": province, "Year": y, "Pass %": r["Passed"].sum() / r["Appeared"].sum()})
    return grouped_year_bar(pd.DataFrame(recs), "Province", YEARS, height=400)


def chart_board_pass_rate(df: pd.DataFrame, year: int) -> go.Figure:
    r = df[df["Year"] == year].sort_values("Pass %age")
    fig = px.bar(r, x="Pass %age", y="Board", orientation="h", text_auto=".1%")
    fig.update_traces(marker_color=COLORS["accent"], textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickformat=".0%", range=[0, 1.1])
    return _base_layout(fig, height=460)


def chart_yoy_change_by_board(df: pd.DataFrame, year: int, other: int) -> go.Figure:
    a = df[df["Year"] == year].set_index("Board")["Pass %age"]
    b = df[df["Year"] == other].set_index("Board")["Pass %age"]
    d = ((a - b).dropna() * 100).sort_values().reset_index()
    d.columns = ["Board", "Change"]
    if d.empty: return empty_fig(f"No boards report both {year} and {other}")
    fig = go.Figure(go.Bar(x=d["Change"], y=d["Board"], orientation="h",
                           marker_color=[COLORS["positive"] if v >= 0 else COLORS["negative"] for v in d["Change"]],
                           text=[f"{v:+.1f}" for v in d["Change"]], textposition="outside", cliponaxis=False))
    pad = max(abs(d["Change"]).max() * 0.2, 2)
    fig.update_xaxes(title="Pass % change (points)", zeroline=True,
                     range=[min(0, d["Change"].min()) - (pad if d["Change"].min() < 0 else 0), max(0, d["Change"].max()) + pad])
    return _base_layout(fig, height=460)


def chart_appeared_share(df: pd.DataFrame, year: int) -> go.Figure:
    r = df[df["Year"] == year]
    fig = px.pie(r, names="Board", values="Appeared", hole=0.55, color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_traces(textinfo="percent", textposition="inside", marker=dict(line=dict(color="white", width=2)))
    _base_layout(fig, height=460)
    fig.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"), margin=dict(t=10, b=70, l=10, r=10))
    return fig


def chart_trend_lines(df: pd.DataFrame) -> go.Figure:
    """Pass % across 2024-2026 per board (the 3-year view the template could not have)."""
    fig = px.line(df.sort_values("Year"), x="Year", y="Pass %age", color="Board", markers=True,
                  color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_xaxes(tickvals=YEARS, tickformat="d", dtick=1)
    fig.update_yaxes(tickformat=".0%")
    _base_layout(fig, "Board", 460)
    fig.update_layout(legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"), margin=dict(t=10, b=70, l=10, r=10))
    return fig


def chart_gender_pass_rate(gender_df: pd.DataFrame) -> go.Figure:
    a = rate(gender_df, ["Year", "Gender"])
    fig = go.Figure()
    for g in ("Male", "Female"):
        s = a[a["Gender"] == g]
        fig.add_trace(go.Bar(x=s["Year"].astype(str), y=s["Pass %"], name=g, marker_color=GENDER_COLORS[g],
                             text=[f"{v:.1%}" for v in s["Pass %"]], textposition="outside", cliponaxis=False))
    fig.update_layout(barmode="group"); fig.update_yaxes(tickformat=".0%", range=[0, 1.1])
    return _base_layout(fig, "Gender")


def chart_gender_share(gender_df: pd.DataFrame, year: int) -> go.Figure:
    a = rate(gender_df[gender_df["Year"] == year], ["Gender"])
    return donut(a, "Gender", "Appeared", GENDER_COLORS)


def chart_category_pass_rate(category_df: pd.DataFrame) -> go.Figure:
    a = rate(category_df, ["Year", "Category"])
    fig = go.Figure()
    for c in ("Regular", "Private"):
        s = a[a["Category"] == c]
        fig.add_trace(go.Bar(x=s["Year"].astype(str), y=s["Pass %"], name=c, marker_color=CATEGORY_COLORS[c],
                             text=[f"{v:.1%}" for v in s["Pass %"]], textposition="outside", cliponaxis=False))
    fig.update_layout(barmode="group"); fig.update_yaxes(tickformat=".0%", range=[0, 1.1])
    return _base_layout(fig, "Category")


def chart_category_share(category_df: pd.DataFrame, year: int) -> go.Figure:
    a = rate(category_df[category_df["Year"] == year], ["Category"])
    return donut(a, "Category", "Appeared", CATEGORY_COLORS)


import json
from pathlib import Path

_GEOJSON_PATH = Path(__file__).resolve().parent.parent / "assets" / "pakistan_provinces.geojson"

# GeoJSON shapeName -> our PROVINCE_BOARD_MAP keys
_GEO_PROVINCE_ALIASES = {
    "Punjab": "Punjab",
    "Khyber Pakhtunkhwa": "Khyber Pakhtunkhwa",
    "Islamabad Capital Territory": "Federal",
}


def _province_totals(overall_df):
    out = {}
    for province, boards in PROVINCE_BOARD_MAP.items():
        sub = overall_df[overall_df["Board"].isin(boards)]
        yd = {}
        for y in YEARS:
            r = sub[sub["Year"] == y]; a, p = int(r["Appeared"].sum()), int(r["Passed"].sum())
            yd[y] = {"appeared": a, "passed": p, "pass_pct": p / a if a else 0.0}
        if any(d["appeared"] > 0 for d in yd.values()): out[province] = yd
    return out


def _map_empty_fallback(message):
    return empty_fig(message, 440)


def chart_pakistan_map(overall_df: pd.DataFrame, year: int = 2026) -> go.Figure:
    """Full-Pakistan choropleth coloured by Appeared in the selected year; hover shows all 3 years."""
    if not _GEOJSON_PATH.exists():
        return _map_empty_fallback("Pakistan map data not found")
    with open(_GEOJSON_PATH, encoding="utf-8") as f:
        geo = json.load(f)
    totals = _province_totals(overall_df)
    locs, zs, hov, vals = [], [], [], []
    for feat in geo["features"]:
        name = feat["properties"]["shapeName"]; prov = _GEO_PROVINCE_ALIASES.get(name)
        locs.append(name)
        if prov and prov in totals:
            t = totals[prov]; zs.append(t[year]["appeared"]); vals.append(t[year]["appeared"])
            lines = "".join(
                f"<br><span style='opacity:.7'>{y}</span> {t[y]['appeared']:,} appeared · {t[y]['passed']:,} passed · <b>{t[y]['pass_pct']*100:.1f}%</b>"
                for y in YEARS if t[y]["appeared"])
            hov.append(f"<b>{name}</b>{lines}<br><span style='opacity:.7'>BISE boards in dataset</span> {len(PROVINCE_BOARD_MAP[prov])}<extra></extra>")
        else:
            zs.append(0)
            hov.append(f"<b>{name}</b><br><span style='opacity:.7'>No BISE board data in this dataset</span><extra></extra>")
    vmax = max(vals) if vals else 1
    grey, blues = COLORS["map_no_data_strong"], COLORS["map_scale"]
    eps = 0.5 / vmax if vmax else 0.0
    cs = [[0.0, grey], [eps, grey]] + [[eps + (i / max(len(blues) - 1, 1)) * (1 - eps), c] for i, c in enumerate(blues)]
    fig = go.Figure(go.Choroplethmap(geojson=geo, featureidkey="properties.shapeName", locations=locs, z=zs,
                                     zmin=0, zmax=vmax, colorscale=cs, showscale=True,
                                     colorbar=dict(title=f"Appeared {year}", thickness=12, len=0.75, tickformat="~s", x=1.0),
                                     marker_line_color="#FFFFFF", marker_line_width=1.2, text=hov,
                                     hovertemplate="%{text}", name=""))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=30.3753, lon=69.3451), zoom=4.3),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color=COLORS["text_on_light"],
                      font_size=12, margin=dict(t=6, b=6, l=6, r=6), height=460,
                      hoverlabel=dict(bgcolor=COLORS["primary"], font_color="#FFFFFF", font_size=12,
                                      bordercolor=COLORS["primary_light"]))
    return fig


def top_movers(df: pd.DataFrame, year: int, other: int) -> tuple:
    """(gainer, decliner) = boards with largest pass-% rise / fall between the two years (boards in both)."""
    a = df[df["Year"] == year].set_index("Board")["Pass %age"]
    b = df[df["Year"] == other].set_index("Board")["Pass %age"]
    d = (a - b).dropna()
    if d.empty: return None, None
    return (d.idxmax(), d.max()), (d.idxmin(), d.min())