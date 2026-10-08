# 12th Class (HSSC) Result Analytics Dashboard — 2024 · 2025 · 2026

Streamlit dashboard built on the template's design (navy topbar, capsule sidebar, KPI cards with sparklines,
white chart cards, Pakistan province map), rebuilt for **three years** of HSSC results across **15 BISE boards**.

## Run
```
pip install -r requirements.txt
streamlit run app.py
```

## Pages
Overview · Board Comparison · Gender Analysis · Group Wise · Regular vs Private · Subject Wise · District Wise · Grade Distribution

## How the data works
`data/BISE_HSSC_MASTER_FINAL_2024-2026.xlsx` has 119 sheets, each board laid out differently.
`data/build_data.py` reads them and writes seven tidy tables to `data/processed/*.csv`
(overall, gender, category, group, subject, district, grade). The dashboard reads only those CSVs.

To update: replace the workbook, run `python data/build_data.py`, and change `LAST_UPDATED` in `config/settings.py`.
If the CSVs are missing, the app rebuilds them on first start.

## Coverage (what each board publishes)
* Overall: all 15 boards. Bannu and Kohat have no 2024; Gujranwala has no 2026; Swat 2024 onward as listed in the workbook.
* Gender / Regular-vs-Private: 15 boards (Bannu 2026 only).
* Group: 14 boards. Subject: 11 boards. Grades: 11 boards. Districts: 8 boards (Bahawalpur 2024 only, Lahore 2026 only).
* Pages only offer boards that have the data, and year changes compare only boards present in both years.
* Grades are for passed candidates; A+, A-1 and A1 are shown as A+.
* Boards that publish nothing for a breakdown are never estimated.
