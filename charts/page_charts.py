"""charts/page_charts.py — charts for pages 2-8 (Board Comparison, Gender, Group, Regular/Private,
Subject, District, Grade).  Everything is driven by tidy tables from data/loader.py and is
year-aware for 2024 / 2025 / 2026.  Pass % is always recomputed as Passed / Appeared."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from charts.label_utils import assign_scatter_label_positions
from charts.common import (YEARS, YEAR_COLORS, GENDER_COLORS, CATEGORY_COLORS, GROUP_COLORS, GRADE_COLORS,
                           GRID, BAR_LABEL_SIZE, compact, base_layout, empty_fig, rate, like_for_like, prev_year,
                           province_of, grouped_year_bar, donut, board_colors, stacked_share_bar, year_axis)

DIM_COLORS = {"Gender": GENDER_COLORS, "Category": CATEGORY_COLORS, "Group": GROUP_COLORS}


# ------------------------------------------------------------ Board comparison
def chart_pass_rate_by_board(ov, years):
    d = ov[ov["Year"].isin(years)].copy()
    d["Pass %"] = d["Pass %age"]
    order = d.groupby("Board")["Pass %"].mean().sort_values(ascending=False).index.tolist()
    return grouped_year_bar(d, "Board", years, height=440, order=order)


def chart_appeared_by_board(ov, years):
    d = ov[ov["Year"].isin(years)]
    return grouped_year_bar(d, "Board", years, y="Appeared", pct=False, height=440)


def chart_board_ranking(ov, year):
    d = ov[ov["Year"] == year].sort_values("Pass %age")
    fig = go.Figure(go.Bar(x=d["Pass %age"], y=d["Board"], orientation="h",
                           marker_color=[COLORS["gold"] if i == len(d) - 1 else COLORS["accent"] for i in range(len(d))],
                           text=[f"{v:.1%}" for v in d["Pass %age"]], textposition="outside", cliponaxis=False))
    fig.update_xaxes(tickformat=".0%", range=[0, 1.1])
    return base_layout(fig, height=460)


def chart_passed_vs_failed(ov, year):
    d = ov[ov["Year"] == year].copy(); d["Failed"] = d["Appeared"] - d["Passed"]
    d = d.sort_values("Appeared")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["Board"], x=d["Passed"], name="Passed", orientation="h", marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(y=d["Board"], x=d["Failed"], name="Failed", orientation="h", marker_color=COLORS["negative"]))
    fig.update_layout(barmode="stack"); fig.update_xaxes(tickformat="~s")
    return base_layout(fig, "", 460)


def chart_size_vs_performance(ov, year):
    d = ov[ov["Year"] == year].copy(); d["Province"] = d["Board"].map(province_of)
    d["lx"] = d["Appeared"].map(math.log10)
    xr = [d["lx"].min() - 0.22, d["lx"].max() + 0.22]
    yr = [max(0.0, d["Pass %age"].min() - 0.10), min(1.0, d["Pass %age"].max() + 0.10)]
    pos = assign_scatter_label_positions(list(d["Board"]), list(d["lx"]), list(d["Pass %age"]), xr, yr,
                                         plot_width=520, plot_height=340, font_size=11, point_radius=20)
    pcol = {"Punjab": COLORS["gold"], "Khyber Pakhtunkhwa": COLORS["accent"], "Federal": COLORS["positive"]}
    mx = d["Appeared"].max() ** 0.5
    fig = go.Figure()
    for prov, g in d.groupby("Province"):
        fig.add_trace(go.Scatter(
            x=g["lx"], y=g["Pass %age"], mode="markers+text", name=prov, text=g["Board"],
            textposition=[pos[(round(float(x), 8), round(float(y), 8), str(t))] for x, y, t in zip(g["lx"], g["Pass %age"], g["Board"])],
            textfont=dict(size=11, color=COLORS["text_on_light"]), customdata=g[["Appeared"]],
            marker=dict(size=g["Appeared"] ** 0.5 / mx * 30 + 10, color=pcol.get(prov), opacity=0.8, line=dict(color="white", width=1.5)),
            hovertemplate="<b>%{text}</b><br>Appeared: %{customdata[0]:,.0f}<br>Pass %: %{y:.1%}<extra></extra>"))
    ticks = [t for t in (10_000, 20_000, 50_000, 100_000, 200_000, 500_000) if 10 ** xr[0] <= t <= 10 ** xr[1]]
    fig.update_xaxes(range=xr, tickvals=[math.log10(t) for t in ticks], ticktext=[compact(t) for t in ticks],
                     title="Candidates appeared (log scale)", showgrid=True)
    fig.update_yaxes(range=yr, tickformat=".0%", title="Pass %")
    base_layout(fig, "Province", 480)
    fig.update_layout(legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center"), margin=dict(t=10, b=70, l=10, r=20))
    return fig


def chart_board_year_heatmap(ov):
    p = ov.pivot(index="Board", columns="Year", values="Pass %age").reindex(columns=YEARS)
    p = p.loc[p.mean(axis=1).sort_values(ascending=False).index]
    fig = go.Figure(go.Heatmap(z=p.values * 100, x=[str(c) for c in p.columns], y=p.index, colorscale=COLORS["map_scale"],
                               text=[[("" if pd.isna(v) else f"{v*100:.1f}%") for v in r] for r in p.values],
                               texttemplate="%{text}", hovertemplate="%{y} %{x}: %{text}<extra></extra>",
                               colorbar=dict(title="Pass %")))
    fig.update_yaxes(autorange="reversed")
    return base_layout(fig, height=460)


def comparison_table(ov, years):
    p = ov[ov["Year"].isin(years)].pivot(index="Board", columns="Year", values=["Appeared", "Passed", "Pass %age"])
    p.columns = [f"{a.replace('Pass %age', 'Pass %')} {y}" for a, y in p.columns]
    for c in p.columns:
        if c.startswith("Pass"): p[c] = (p[c] * 100).round(2)
    return p.reset_index()


# ------------------------------------------------ generic breakdown (gender / group / category)
def _agg(df, dim, boards, years=None):
    d = df[df["Board"].isin(boards)]
    if years: d = d[d["Year"].isin(years)]
    return rate(d, ["Board", "Year", dim])


def dim_kpis(df, dim, boards, year, other):
    """Overall pass % per dim value for year vs other, plus best/worst value."""
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], [dim]).set_index(dim)
    out = {"a": a}
    if other:
        sub = like_for_like(df[df["Board"].isin(boards)], year, other)
        out["b"] = rate(sub[sub["Year"] == other], [dim]).set_index(dim)
        out["a_ll"] = rate(sub[sub["Year"] == year], [dim]).set_index(dim)
    return out


def chart_dim_trend(df, dim, boards):
    """Pass % by dim value across the 3 years (aggregate of selected boards)."""
    a = rate(df[df["Board"].isin(boards)], ["Year", dim])
    colors = DIM_COLORS[dim]
    fig = go.Figure()
    for v in sorted(a[dim].unique()):
        s = a[a[dim] == v].sort_values("Year")
        fig.add_trace(go.Scatter(x=s["Year"].astype(str), y=s["Pass %"], name=str(v), mode="lines+markers+text",
                                 line=dict(color=colors.get(v), width=3), marker=dict(size=9),
                                 text=[f"{x:.1%}" for x in s["Pass %"]], textposition="top center"))
    fig.update_yaxes(tickformat=".0%")
    year_axis(fig)
    base_layout(fig, dim, 400)
    fig.update_layout(legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"), margin=dict(t=20, b=50, l=10, r=10))
    return fig


def chart_dim_by_board(df, dim, boards, year):
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], ["Board", dim])
    if a.empty: return empty_fig()
    order = a.groupby("Board")["Pass %"].mean().sort_values(ascending=False).index.tolist()
    colors = DIM_COLORS[dim]
    vals = sorted(a[dim].unique())
    horiz = len(order) * len(vals) > 9     # many bars -> horizontal bars with straight labels
    fig = go.Figure()
    for v in vals:
        s = a[a[dim] == v]
        kw = dict(name=str(v), marker_color=colors.get(v), text=[f"{x:.1%}" for x in s["Pass %"]],
                  textposition="outside", textangle=0,
                  textfont=dict(size=BAR_LABEL_SIZE, color=COLORS["text_on_light"]), cliponaxis=False)
        fig.add_trace(go.Bar(x=s["Pass %"], y=s["Board"], orientation="h", **kw) if horiz
                      else go.Bar(x=s["Board"], y=s["Pass %"], **kw))
    fig.update_layout(barmode="group")
    if horiz:
        fig.update_xaxes(tickformat=".0%", range=[0, 1.12], tickvals=[0, .2, .4, .6, .8, 1])
        fig.update_yaxes(categoryorder="array", categoryarray=order, autorange="reversed")
        base_layout(fig, dim, max(440, len(order) * (len(vals) * 18 + 12) + 60))
        fig.update_layout(bargap=0.18, bargroupgap=0.05, margin=dict(t=10, b=10, l=10, r=40))
    else:
        fig.update_yaxes(tickformat=".0%", range=[0, 1.12], tickvals=[0, .2, .4, .6, .8, 1])
        fig.update_xaxes(categoryorder="array", categoryarray=order)
        base_layout(fig, dim, 440)
    return fig


def chart_dim_gap(df, dim, hi, lo, boards, year):
    """Gap (percentage points) between two dim values per board (e.g. Female - Male)."""
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], ["Board", dim])
    p = a.pivot(index="Board", columns=dim, values="Pass %")
    if hi not in p or lo not in p: return empty_fig()
    g = ((p[hi] - p[lo]) * 100).dropna().sort_values().reset_index(); g.columns = ["Board", "Gap"]
    fig = go.Figure(go.Bar(x=g["Gap"], y=g["Board"], orientation="h",
                           marker_color=[COLORS["gold"] if v >= 0 else COLORS["accent"] for v in g["Gap"]],
                           text=[f"{v:+.1f}" for v in g["Gap"]], textposition="outside", cliponaxis=False))
    pad = max(abs(g["Gap"]).max() * 0.2, 3)
    fig.update_xaxes(title=f"{hi} minus {lo} pass % (points)", zeroline=True,
                     range=[min(0, g["Gap"].min()) - (pad if g["Gap"].min() < 0 else 0), max(0, g["Gap"].max()) + pad])
    return base_layout(fig, height=440)


def chart_dim_share_by_board(df, dim, boards, year):
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], ["Board", dim])
    if a.empty: return empty_fig()
    a["Share"] = a["Appeared"] / a.groupby("Board")["Appeared"].transform("sum")
    order = a.groupby("Board")["Appeared"].sum().sort_values().index.tolist()
    return stacked_share_bar(a, "Board", dim, "Share", DIM_COLORS[dim], order=order, color_order=sorted(a[dim].unique()))

def chart_dim_donut(df, dim, boards, year):
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], [dim])
    return donut(a, dim, "Appeared", DIM_COLORS[dim]) if not a.empty else empty_fig()


def chart_dim_heatmap(df, dim, boards, year):
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], ["Board", dim])
    if a.empty: return empty_fig()
    p = a.pivot(index="Board", columns=dim, values="Pass %")
    fig = go.Figure(go.Heatmap(z=p.values * 100, x=list(p.columns), y=list(p.index), colorscale=COLORS["map_scale"],
                               text=[[("" if pd.isna(v) else f"{v*100:.0f}%") for v in r] for r in p.values],
                               texttemplate="%{text}", colorbar=dict(title="Pass %"),
                               hovertemplate="%{y} · %{x}: %{text}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return base_layout(fig, height=440)


def chart_dim_box(df, dim, boards, years):
    """Aggregate pass % per dim value, one bar per year (replaces the cluttered box plot)."""
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"].isin(years))], ["Year", dim])
    if a.empty: return empty_fig()
    order = a.groupby(dim)["Pass %"].mean().sort_values(ascending=False).index.tolist()
    return grouped_year_bar(a, dim, years, height=400, order=order)

def chart_dim_treemap(df, dim, boards, year):
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], ["Board", dim])
    if a.empty: return empty_fig()
    fig = px.treemap(a, path=[dim, "Board"], values="Appeared", color="Pass %", color_continuous_scale=COLORS["map_scale"])
    return base_layout(fig, height=440)


def dim_table(df, dim, boards, year):
    a = rate(df[(df["Board"].isin(boards)) & (df["Year"] == year)], ["Board", dim])
    a["Pass %"] = (a["Pass %"] * 100).round(2)
    return a.rename(columns={"Passed": "Passed", "Failed": "Failed"}).sort_values(["Board", dim]).reset_index(drop=True)


# ------------------------------------------------------------------------ Subjects
def _subj(df, boards, year):
    d = df[(df["Board"].isin(boards)) & (df["Year"] == year)]
    s = rate(d, ["Subject"]); s = s[s["Appeared"] >= 30]
    return s


def chart_subject_best_worst(df, boards, year, n=10):
    s = _subj(df, boards, year)
    if len(s) < 2: return empty_fig()
    s = s.sort_values("Pass %"); n = min(n, len(s) // 2)
    d = pd.concat([s.head(n).assign(Tier="Lowest"), s.tail(n).assign(Tier="Highest")])
    d["Full"] = d["Subject"]
    d["Subject"] = [t if len(t) <= 34 else t[:33].rstrip() + "…" for t in d["Subject"]]
    fig = px.bar(d, x="Pass %", y="Subject", color="Tier", orientation="h", text=[f"{v:.1%}" for v in d["Pass %"]],
                 hover_data={"Full": True, "Subject": False},
                 color_discrete_map={"Lowest": COLORS["negative"], "Highest": COLORS["positive"]})
    fig.update_xaxes(tickformat=".0%", range=[0, 1.1]); fig.update_yaxes(autorange="reversed", categoryorder="array",
                                                                       categoryarray=list(d["Subject"]))
    fig.update_traces(textposition="outside", cliponaxis=False)
    return base_layout(fig, "", 560)


def chart_subject_scatter(df, boards, year):
    s = _subj(df, boards, year)
    if s.empty: return empty_fig()
    fig = px.scatter(s, x="Appeared", y="Pass %", size="Appeared", color="Pass %", hover_name="Subject", size_max=40, log_x=True,
                     color_continuous_scale=["#EF4444", "#C9A84C", "#22C55E"])
    fig.update_traces(marker=dict(opacity=0.8, line=dict(color="white", width=1)))
    fig.update_yaxes(tickformat=".0%")
    return base_layout(fig, height=460)


def chart_subject_heatmap(df, boards, year, top_n=18):
    d = df[(df["Board"].isin(boards)) & (df["Year"] == year)]
    a = rate(d, ["Board", "Subject"]); a = a[a["Appeared"] >= 30]
    top = a.groupby("Subject")["Appeared"].sum().nlargest(top_n).index
    p = a[a["Subject"].isin(top)].pivot(index="Subject", columns="Board", values="Pass %")
    if p.empty: return empty_fig()
    fig = go.Figure(go.Heatmap(z=p.values * 100, x=list(p.columns), y=list(p.index), colorscale=COLORS["map_scale"],
                               text=[[("" if pd.isna(v) else f"{v*100:.0f}") for v in r] for r in p.values],
                               texttemplate="%{text}", colorbar=dict(title="Pass %"),
                               hovertemplate="%{y} · %{x}: %{text}%<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return base_layout(fig, height=560)


def chart_subject_trend(df, boards, top_n=8):
    d = df[df["Board"].isin(boards)]
    a = rate(d, ["Year", "Subject"])
    top = rate(d, ["Subject"]).nlargest(top_n, "Appeared")["Subject"]
    a = a[a["Subject"].isin(top)]
    if a.empty: return empty_fig()
    fig = px.line(a.sort_values("Year"), x="Year", y="Pass %", color="Subject", markers=True,
                  color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_xaxes(tickvals=YEARS, tickformat="d", dtick=1); fig.update_yaxes(tickformat=".0%")
    return base_layout(fig, "Subject", 440)


def chart_subject_treemap(df, boards, year, top_n=40):
    s = _subj(df, boards, year).nlargest(top_n, "Appeared")
    if s.empty: return empty_fig()
    fig = px.treemap(s, path=["Subject"], values="Appeared", color="Pass %", color_continuous_scale=COLORS["map_scale"])
    return base_layout(fig, height=460)


def subject_table(df, boards, year):
    s = _subj(df, boards, year).sort_values("Pass %", ascending=False)
    s["Pass %"] = (s["Pass %"] * 100).round(2)
    return s.reset_index(drop=True)


# ------------------------------------------------------------------------ Districts
def chart_district_rate(df, board, years):
    d = df[df["Board"] == board]
    a = rate(d[d["Year"].isin(years)], ["District", "Year"])
    if a.empty: return empty_fig()
    order = a.groupby("District")["Pass %"].mean().sort_values(ascending=False).index.tolist()
    return grouped_year_bar(a, "District", years, height=460, order=order)


def chart_district_appeared(df, board, years):
    a = rate(df[(df["Board"] == board) & (df["Year"].isin(years))], ["District", "Year"])
    return grouped_year_bar(a, "District", years, y="Appeared", pct=False, height=440) if not a.empty else empty_fig()


def chart_district_scatter(df, board, year):
    a = rate(df[(df["Board"] == board) & (df["Year"] == year)], ["District"])
    if a.empty: return empty_fig()
    xr = [0, a["Appeared"].max() * 1.15]
    yr = [max(0.0, a["Pass %"].min() - 0.08), min(1.0, a["Pass %"].max() + 0.08)]
    pos = assign_scatter_label_positions(list(a["District"]), list(a["Appeared"]), list(a["Pass %"]), xr, yr,
                                         plot_width=520, plot_height=340, font_size=11, point_radius=14)
    fig = go.Figure(go.Scatter(
        x=a["Appeared"], y=a["Pass %"], mode="markers+text", text=a["District"],
        textposition=[pos[(round(float(x), 8), round(float(y), 8), str(t))] for x, y, t in zip(a["Appeared"], a["Pass %"], a["District"])],
        textfont=dict(size=11), marker=dict(size=a["Appeared"] ** 0.5 / a["Appeared"].max() ** 0.5 * 26 + 8,
                                            color=[BOARD_COLOR_SEQUENCE[i % len(BOARD_COLOR_SEQUENCE)] for i in range(len(a))],
                                            opacity=0.85, line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{text}</b><br>Appeared: %{x:,.0f}<br>Pass %: %{y:.1%}<extra></extra>"))
    fig.update_xaxes(range=xr, tickformat="~s", title="Candidates appeared"); fig.update_yaxes(range=yr, tickformat=".0%", title="Pass %")
    return base_layout(fig, height=440)


def chart_district_treemap(df, board, year):
    a = rate(df[(df["Board"] == board) & (df["Year"] == year)], ["District"])
    if a.empty: return empty_fig()
    fig = px.treemap(a, path=["District"], values="Appeared", color="Pass %", color_continuous_scale=COLORS["map_scale"])
    return base_layout(fig, height=440)


def chart_district_pass_fail(df, board, year):
    a = rate(df[(df["Board"] == board) & (df["Year"] == year)], ["District"])
    if a.empty: return empty_fig()
    a = a.sort_values("Appeared")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=a["District"], x=a["Passed"], name="Passed", orientation="h", marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(y=a["District"], x=a["Failed"], name="Failed", orientation="h", marker_color=COLORS["negative"]))
    fig.update_layout(barmode="stack"); fig.update_xaxes(tickformat="~s")
    return base_layout(fig, "", 440)


def chart_district_trend(df, board):
    a = rate(df[df["Board"] == board], ["District", "Year"])
    if a["Year"].nunique() < 2: return empty_fig("This board publishes district data for one year only")
    fig = px.line(a.sort_values("Year"), x="Year", y="Pass %", color="District", markers=True,
                  color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_xaxes(tickvals=YEARS, tickformat="d", dtick=1); fig.update_yaxes(tickformat=".0%")
    return base_layout(fig, "District", 440)


def district_table(df, board, year):
    a = rate(df[(df["Board"] == board) & (df["Year"] == year)], ["District"])
    a["Pass %"] = (a["Pass %"] * 100).round(2)
    return a.sort_values("Pass %", ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------------ Grades
def _gshare(df, boards, year):
    d = df[(df["Board"].isin(boards)) & (df["Year"] == year)]
    d = d.groupby(["Board", "Grade"])["Count"].sum().reset_index()
    d["Share"] = d["Count"] / d.groupby("Board")["Count"].transform("sum")
    return d


def chart_grade_stacked(df, boards, year):
    d = _gshare(df, boards, year)
    if d.empty: return empty_fig()
    top = d[d["Grade"] == "A+"].set_index("Board")["Share"]
    order = top.reindex(d["Board"].unique()).fillna(0).sort_values().index.tolist()
    return stacked_share_bar(d, "Board", "Grade", "Share", GRADE_COLORS, order=order, color_order=list(GRADE_COLORS))

def chart_grade_donut(df, boards, year):
    d = df[(df["Board"].isin(boards)) & (df["Year"] == year)].groupby("Grade")["Count"].sum().reset_index()
    return donut(d, "Grade", "Count", GRADE_COLORS) if not d.empty else empty_fig()


def chart_grade_heatmap(df, boards, year):
    d = _gshare(df, boards, year)
    if d.empty: return empty_fig()
    p = d.pivot(index="Board", columns="Grade", values="Share").reindex(columns=list(GRADE_COLORS))
    fig = go.Figure(go.Heatmap(z=p.values * 100, x=list(p.columns), y=list(p.index), colorscale=COLORS["map_scale"],
                               text=[[("" if pd.isna(v) else f"{v*100:.0f}%") for v in r] for r in p.values],
                               texttemplate="%{text}", colorbar=dict(title="Share %")))
    fig.update_yaxes(autorange="reversed")
    return base_layout(fig, height=440)


def chart_grade_year_mix(df, boards):
    d = df[df["Board"].isin(boards)].groupby(["Year", "Grade"])["Count"].sum().reset_index()
    if d.empty: return empty_fig()
    d["Share"] = d["Count"] / d.groupby("Year")["Count"].transform("sum")
    d["Y"] = d["Year"].astype(str)
    fig = px.bar(d, x="Y", y="Share", color="Grade", color_discrete_map=GRADE_COLORS,
                 category_orders={"Grade": list(GRADE_COLORS)}, text_auto=".0%")
    fig.update_xaxes(type="category", title="")
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    base_layout(fig, "Grade", 420)
    fig.update_layout(legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
    return fig


def chart_top_grade_share(df, boards, years):
    d = df[(df["Board"].isin(boards)) & (df["Year"].isin(years))].groupby(["Board", "Year", "Grade"])["Count"].sum().reset_index()
    d["Share"] = d["Count"] / d.groupby(["Board", "Year"])["Count"].transform("sum")
    d = d[d["Grade"] == "A+"]
    if d.empty: return empty_fig()
    order = d.groupby("Board")["Share"].mean().sort_values(ascending=False).index.tolist()
    return grouped_year_bar(d, "Board", years, y="Share", height=440, order=order)


def grade_table(df, boards, year):
    d = df[(df["Board"].isin(boards)) & (df["Year"] == year)]
    p = d.pivot_table(index="Board", columns="Grade", values="Count", aggfunc="sum").reindex(columns=list(GRADE_COLORS))
    p["Total graded"] = p.sum(axis=1)
    return p.reset_index()