"""components/page_boot.py — the shared page skeleton (CSS, sidebar, topbar) + small UI helpers."""
import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar
from components.kpi_card import render_kpi_row, format_compact
from charts.common import YEARS, prev_year


def boot(page, subtitle, stat_label="BISE Boards", stat_value="15", stat_icon="account_balance"):
    st.set_page_config(page_title=f"{page} - {APP_NAME}", page_icon=PAGE_ICON, layout="wide")
    inject_css()
    render_sidebar()
    render_topbar(active_page=page, subtitle=subtitle, stat_label=stat_label, stat_value=stat_value, stat_icon=stat_icon)


def delta_kpi(cur, prv, fmt=format_compact, pct=False, invert=False):
    """-> (delta_text, positive) comparing cur to prv; pct=True means values are fractions (shown as points)."""
    if prv is None or cur is None: return "", True
    d = cur - prv
    if pct: txt = f"{abs(d)*100:.1f} pts"
    else: txt = fmt(abs(d))
    good = d >= 0
    return txt, (not good if invert else good)


def years_note(year, other, boards_note=""):
    if other: st.caption(f"Changes compare {year} with {other}, using only boards that published both years. {boards_note}")
    else: st.caption(f"{year} is the first year in the dataset, so there is no earlier year to compare with. {boards_note}")
