"""charts/common.py — shared helpers for every chart module (3-year aware)."""
import pandas as pd
import plotly.graph_objects as go
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from data.availability import PROVINCE_BOARD_MAP

YEARS = [2024, 2025, 2026]
YEAR_COLORS = {2024: COLORS["trend_2024"], 2025: COLORS["trend_2025"], 2026: COLORS["trend_2026"]}
GENDER_COLORS = {"Male": COLORS["accent"], "Female": COLORS["gold"]}
CATEGORY_COLORS = {"Regular": COLORS["accent"], "Private": COLORS["gold"]}
GROUP_COLORS = {"Pre-Medical": "#3B82F6", "Pre-Engineering": "#C9A84C", "General Science": "#22C55E",
                "Humanities": "#A855F7", "Commerce": "#F97316", "Home Economics": "#EC4899", "Other": "#9CA3AF"}
GRADE_COLORS = {"A+": "#0B1E4D", "A": "#1D4ED8", "B": "#3B82F6", "C": "#79AFFF", "D": "#C9A84C", "E": "#EF4444"}
GRID = "rgba(20,27,60,0.08)"


def board_colors(boards):
    return {b: BOARD_COLOR_SEQUENCE[i % len(BOARD_COLOR_SEQUENCE)] for i, b in enumerate(sorted(boards))}


def compact(v) -> str:
    v = float(v)
    if abs(v) >= 1e6: return f"{v/1e6:.2f}M"
    if abs(v) >= 1e3: return f"{v/1e3:.1f}K"
    return f"{v:,.0f}"


BAR_LABEL_SIZE = 14   # value labels on every bar chart (increase here to enlarge all of them)


def base_layout(fig, legend_title="", height=400):
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color=COLORS["text_on_light"], font_size=13, legend_title_text=legend_title,
                      margin=dict(t=10, b=10, l=10, r=10), height=height,
                      uniformtext_mode=False, bargap=0.35)
    fig.update_traces(textfont_size=BAR_LABEL_SIZE, constraintext="none", selector=dict(type="bar"))   # constraintext=none: stop Plotly shrinking labels to the bar width
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def empty_fig(msg="No data available for this selection", height=300):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), height=height,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      annotations=[dict(text=msg, showarrow=False, font=dict(color=COLORS["text_on_light_muted"], size=14))])
    return fig


def rate(df, keys):
    """Sum Appeared/Passed by keys and recompute Pass % from raw counts."""
    g = df.groupby(keys, dropna=False)[["Appeared", "Passed"]].sum().reset_index()
    g["Failed"] = g["Appeared"] - g["Passed"]
    g["Pass %"] = g["Passed"] / g["Appeared"]
    return g


def like_for_like(df, y1, y2, board_col="Board"):
    """Restrict to boards that have data in BOTH years, so deltas compare like with like."""
    a = set(df[df["Year"] == y1][board_col]); b = set(df[df["Year"] == y2][board_col])
    return df[df[board_col].isin(a & b)]


def prev_year(year, years=YEARS):
    ys = [y for y in years if y < year]
    return ys[-1] if ys else None


def province_of(board):
    for p, bs in PROVINCE_BOARD_MAP.items():
        if board in bs: return p
    return "Other"


def grouped_year_bar(agg, x, years, y="Pass %", pct=True, title_y=None, height=400, order=None):
    """Few bars -> normal grouped columns (one per year).
    Many bars -> ONE horizontal bar per category, divided into one SECTION per year (2024 | 2025 | 2026).
    Inside its section each year is filled to its own value (93% fills 93% of the section) and the
    value is written straight at the END of the fill; the unfilled rest of the section is light grey."""
    fig = go.Figure()
    n_cats = agg[x].nunique() if len(agg) else 0
    horiz = n_cats * len(years) > 9
    if not horiz:
        for yr in years:
            s = agg[agg["Year"] == yr]
            if s.empty: continue
            fig.add_trace(go.Bar(x=s[x], y=s[y], name=str(yr), marker_color=YEAR_COLORS[yr],
                                 text=[f"{v:.1%}" if pct else compact(v) for v in s[y]],
                                 textposition="outside", textangle=0,
                                 textfont=dict(size=BAR_LABEL_SIZE, color=COLORS["text_on_light"]), cliponaxis=False))
        fig.update_layout(barmode="group")
        if pct:
            mx = float(agg[y].max()) if len(agg) else 1.0
            if mx > 0.6: fig.update_yaxes(tickformat=".0%", range=[0, 1.12], tickvals=[0, .2, .4, .6, .8, 1])
            else:        fig.update_yaxes(tickformat=".0%", range=[0, mx * 1.15])
        else:
            top = float(agg[y].max()) if len(agg) else 1.0
            fig.update_yaxes(tickformat="~s", range=[0, top * 1.12])
        if order: fig.update_xaxes(categoryorder="array", categoryarray=order)
        base_layout(fig, "Year", height)
        return fig

    # ---- one bar per category, one section per year ----
    height = max(height, n_cats * 34 + 80)
    cats = list(order) if order else list(agg.groupby(x)[y].mean().sort_values(ascending=False).index)
    mx = float(agg[y].max()) if len(agg) else 1.0
    denom = 1.0 if (pct and mx > 0.6) else mx * 1.05          # what a completely filled section stands for
    n = len(years); w = 1.0 / n                                # width of one section on the 0..1 axis
    lab = {2024: COLORS["text_on_light"], 2025: COLORS["text_on_light"], 2026: "white"}
    for yr in years:
        s = agg[agg["Year"] == yr].set_index(x)[y]
        vals = [float(s[c]) if c in s.index and pd.notna(s[c]) else None for c in cats]
        fill = [min(v / denom, 1.0) * w if v is not None else 0 for v in vals]
        fig.add_trace(go.Bar(x=fill, y=cats, orientation="h", name=str(yr), marker_color=YEAR_COLORS[yr],
                             text=[(f"{v:.1%}" if pct else compact(v)) if v is not None else "" for v in vals],
                             textposition="inside", insidetextanchor="end", textangle=0, constraintext="none",
                             textfont=dict(size=BAR_LABEL_SIZE, color=lab.get(yr, "white")),
                             customdata=[[("n/a" if v is None else (f"{v:.1%}" if pct else f"{v:,.0f}"))] for v in vals],
                             hovertemplate="%{y} &middot; " + str(yr) + ": %{customdata[0]}<extra></extra>"))
        fig.add_trace(go.Bar(x=[w - f for f in fill], y=cats, orientation="h", marker_color="rgba(148,163,184,0.18)",
                             showlegend=False, hoverinfo="skip"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(range=[0, 1], tickvals=[w * (i + .5) for i in range(n)], ticktext=[str(y_) for y_ in years],
                     showgrid=False, side="top", tickfont=dict(size=14))
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=cats)
    base_layout(fig, "Year", height)
    fig.update_layout(bargap=0.22, margin=dict(t=10, b=10, l=10, r=20), legend=dict(traceorder="normal"))
    return fig


def donut(df, names, values, colors=None, height=360):
    """Donut with in-slice % labels (hidden when too small) and a bottom legend, so nothing overlaps or clips."""
    fig = go.Figure(go.Pie(labels=df[names], values=df[values], hole=0.55, sort=False,
                           marker=dict(colors=[(colors or {}).get(n) for n in df[names]] if colors else None,
                                       line=dict(color="white", width=2)),
                           textinfo="percent", textposition="inside", insidetextorientation="horizontal"))
    fig.update_layout(legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"), showlegend=True)
    base_layout(fig, height=height)
    fig.update_layout(margin=dict(t=10, b=40, l=10, r=10), uniformtext_minsize=11, uniformtext_mode="hide")
    return fig


def stacked_share_bar(a, y, color, value, colors, order=None, color_order=None, height=460, min_label=0.07):
    """100% horizontal stacked bars: legend under the chart, labels only on segments >= min_label, axis fixed 0-100%."""
    fig = go.Figure()
    cats = color_order or list(a[color].unique())
    for c in cats:
        s = a[a[color] == c]
        if s.empty: continue
        fig.add_trace(go.Bar(y=s[y], x=s[value], name=str(c), orientation="h", marker_color=(colors or {}).get(c),
                             text=[f"{v:.0%}" if v >= min_label else "" for v in s[value]],
                             textposition="inside", insidetextanchor="middle",
                             textfont=dict(color="white", size=BAR_LABEL_SIZE), cliponaxis=False,
                             hovertemplate="%{y} · " + str(c) + ": %{x:.1%}<extra></extra>"))
    fig.update_layout(barmode="stack", legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center", title_text=""))
    fig.update_xaxes(tickformat=".0%", range=[0, 1], title="")
    fig.update_yaxes(title="", automargin=True)
    if order: fig.update_yaxes(categoryorder="array", categoryarray=order)
    base_layout(fig, height=height)
    fig.update_layout(margin=dict(t=10, b=60, l=10, r=10), bargap=0.25)
    return fig


def year_axis(fig):
    """Show only whole years (2024, 2025, 2026) on a numeric/string year axis."""
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=[str(y) for y in YEARS])
    return fig