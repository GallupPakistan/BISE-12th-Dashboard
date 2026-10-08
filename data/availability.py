"""
data/availability.py

Which boards publish which breakdown is computed from the processed tables,
so it can never drift from the data.  Only PROVINCE_BOARD_MAP is static.
"""
import pandas as pd
from pathlib import Path

_P = Path(__file__).resolve().parent / "processed"


def _boards(kind):
    f = _P / f"{kind}.csv"
    return sorted(pd.read_csv(f)["Board"].unique()) if f.exists() else []


GENDER_AVAILABLE_BOARDS = _boards("gender")
CATEGORY_AVAILABLE_BOARDS = _boards("category")
GROUP_AVAILABLE_BOARDS = _boards("group")
SUBJECT_AVAILABLE_BOARDS = _boards("subject")
DISTRICT_AVAILABLE_BOARDS = _boards("district")
GRADE_AVAILABLE_BOARDS = _boards("grade")

PROVINCE_BOARD_MAP = {
    "Federal": ["FBISE"],
    "Punjab": [
        "Lahore", "Rawalpindi", "Gujranwala", "FSD", "Sargodha",
        "Sahiwal", "Bahawalpur", "DGK",
    ],
    "Khyber Pakhtunkhwa": [
        "Peshawar", "Swat", "Abbottabad", "Mardan", "Kohat", "Bannu",
    ],
}