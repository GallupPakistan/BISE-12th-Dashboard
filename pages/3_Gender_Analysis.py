"""pages/3_Gender_Analysis.py"""
from components.breakdown_page import render_breakdown
from data.loader import load_gender_table
render_breakdown("Gender Analysis", "Male vs Female results across boards, 2024-2026.", load_gender_table(), "Gender",
                 ["Male", "Female"], "Female", "Male", "gen", [("male", "blue"), ("female", "gold")])
