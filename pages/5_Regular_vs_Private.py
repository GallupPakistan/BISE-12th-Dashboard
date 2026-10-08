"""pages/5_Regular_vs_Private.py"""
from components.breakdown_page import render_breakdown
from data.loader import load_category_table
render_breakdown("Regular vs Private", "Regular and Private candidates compared, 2024-2026.", load_category_table(), "Category",
                 ["Regular", "Private"], "Regular", "Private", "cat", [("school", "blue"), ("person", "gold")])
