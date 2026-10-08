"""
data/loader.py

The ONLY place the dashboard reads data.  Everything comes from the tidy CSVs in
data/processed/ (built from the master workbook by data/build_data.py).
If the CSVs are missing (fresh clone) they are built automatically.
"""
from pathlib import Path
import pandas as pd
import streamlit as st

_P = Path(__file__).resolve().parent / "processed"


def _ensure():
    if not (_P / "overall.csv").exists():
        import runpy
        runpy.run_path(str(Path(__file__).resolve().parent / "build_data.py"))


@st.cache_data(show_spinner="Loading data...")
def load_table(kind: str) -> pd.DataFrame:
    """kind: overall | gender | category | group | subject | district | grade"""
    _ensure()
    return pd.read_csv(_P / f"{kind}.csv")


def load_overall_summary() -> pd.DataFrame:
    return load_table("overall")


def load_gender_table():   return load_table("gender")
def load_category_table(): return load_table("category")
def load_group_table():    return load_table("group")
def load_subject_table():  return load_table("subject")
def load_district_table(): return load_table("district")
def load_grade_table():    return load_table("grade")
