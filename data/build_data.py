"""
data/build_data.py

ETL: reads the HSSC master workbook (119 sheets, every board laid out differently)
and writes 7 normalised tidy tables to data/processed/*.csv.  The dashboard only
ever reads those CSVs (see data/loader.py), so every page/chart is board-agnostic.

Run after replacing the workbook:   python data/build_data.py

Tables
  overall   Board, Year, Appeared, Passed, Pass %age (0-1), Published, Notes
  gender    Board, Year, Gender (Male/Female), Appeared, Passed
  category  Board, Year, Category (Regular/Private), Appeared, Passed
  group     Board, Year, Group, Appeared, Passed
  subject   Board, Year, Subject, Appeared, Passed
  district  Board, Year, District, Appeared, Passed
  grade     Board, Year, Grade (A+,A,B,C,D,E), Count   (counts of PASSED candidates)
"""
import re
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "BISE_HSSC_MASTER_FINAL_2024-2026.xlsx"
OUT = ROOT / "processed"
OUT.mkdir(exist_ok=True)

xl = pd.ExcelFile(XLSX)
GRADES = ["A+", "A", "B", "C", "D", "E"]
BOARD_ALIAS = {"D.G. Khan": "DGK", "Faisalabad": "FSD"}

R = {k: [] for k in ["gender", "category", "group", "subject", "district", "grade"]}


# ---------------------------------------------------------------- helpers
def sheet(name, header=None):
    """Load a sheet; header row auto-detected (first row with >=3 filled cells)."""
    raw = xl.parse(name, header=None)
    if header is None:
        header = 0
        for i in range(min(6, len(raw))):
            if raw.iloc[i].notna().sum() >= 3:
                header = i
                # A real header row is text. If this row holds numbers it is DATA (the sheet has
                # no header row, e.g. 'BWP 2026 Grand Total'), so use the blank row above it as
                # the header instead of swallowing the first data row.
                if i > 0 and pd.to_numeric(raw.iloc[i].dropna(), errors="coerce").notna().any():
                    header = i - 1
                break
    df = xl.parse(name, header=header)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def num(s):
    if not isinstance(s, (pd.Series, pd.DataFrame)):
        s = pd.Series(s if hasattr(s, "__len__") and not isinstance(s, str) else [s])
    return pd.to_numeric(s, errors="coerce")


def col(df, *needles):
    """first column whose lowercase name contains all needles"""
    for c in df.columns:
        lc = c.lower()
        if all(n.lower() in lc for n in needles):
            return c
    raise KeyError(needles)


def canon_group(t):
    s = str(t).lower().replace(".", "").replace("-", " ")
    if "total" in s or s in ("all", "all groups", "nan", "additional", "overall"):
        return None
    if "medical" in s and "tech" not in s and "lab" not in s or s.startswith("pre med") or s == "pre medical":
        return "Pre-Medical"
    if "engin" in s:
        return "Pre-Engineering"
    if "general" in s or "computer" in s or "sc gen" in s or "science general" in s:
        return "General Science"
    if "human" in s:
        return "Humanities"
    if "commerce" in s:
        return "Commerce"
    if "home" in s and "eco" in s:
        return "Home Economics"
    return "Other"


def gender_of(t):
    s = str(t).lower()
    if re.search(r"female|girl", s):
        return "Female"
    if re.search(r"male|boy", s):
        return "Male"
    return None


def cat_of(t):
    s = str(t).lower()
    if "regular" in s or s.startswith("reg"):
        return "Regular"
    if "private" in s or s.startswith("pvt"):
        return "Private"
    return None


def add(kind, board, df, year="Year", **cols):
    """Append (Board, Year, <key cols>, Appeared, Passed) rows to R[kind]."""
    d = df.copy()
    d["Board"] = board
    keep = {"Board": "Board", year: "Year"}
    keep.update({v: k for k, v in cols.items()})
    d = d.rename(columns={v: k for k, v in keep.items() if v != k and k in d.columns} if False else {})
    out = pd.DataFrame({"Board": board, "Year": num(d[year]).astype("Int64")})
    for k, v in cols.items():
        out[k] = d[v].values if isinstance(v, str) else v
    R[kind].append(out)


def push(kind, board, year, key_name, key, app, pas):
    key = list(key) if hasattr(key, "__len__") and not isinstance(key, str) else [key]
    n = len(key)
    yr = list(num(year)) if hasattr(year, "__len__") else [year] * n
    if len(yr) == 1 and n > 1:
        yr = yr * n
    R[kind].append(pd.DataFrame({
        "Board": board, "Year": pd.array(yr[:n], dtype="float").astype("Int64") if False else yr[:n],
        key_name: key, "Appeared": list(num(app)), "Passed": list(num(pas))}))


def push_grades(board, year, df_grades):
    """df_grades: DataFrame indexed any, with Year col + GRADES columns."""
    g = df_grades.copy()
    for k in GRADES:
        g[k] = num(g[k])
    s = g.groupby("Year")[GRADES].sum(min_count=1).reset_index().melt("Year", var_name="Grade", value_name="Count")
    s["Board"] = board
    s = s.dropna(subset=["Count"])
    s = s[s["Count"] > 0]
    R["grade"].append(s[["Board", "Year", "Grade", "Count"]])


def generic(board, df, year, app, pas, gender=None, category=None, group=None,
            grades=None, mask=None):
    """Summarise a detail-level frame into gender / category / group / grade tables."""
    d = df if mask is None else df[mask]
    d = d.copy()
    d["_Y"] = num(d[year]) if year in d.columns else year
    d["_A"], d["_P"] = num(d[app]), num(d[pas])
    for kind, src, fn in (("gender", gender, gender_of), ("category", category, cat_of),
                          ("group", group, canon_group)):
        if src is None:
            continue
        k = d[src].map(fn) if callable(fn) else d[src]
        t = d.assign(_K=k).dropna(subset=["_K"]).groupby(["_Y", "_K"])[["_A", "_P"]].sum().reset_index()
        t.columns = ["Year", {"gender": "Gender", "category": "Category", "group": "Group"}[kind], "Appeared", "Passed"]
        t.insert(0, "Board", board)
        R[kind].append(t)
    if grades:
        g = d[["_Y"] + grades].rename(columns={"_Y": "Year", **dict(zip(grades, GRADES))})
        push_grades(board, None, g)


# ----------------------------------------------------------------- overall
ms = xl.parse("Master Summary", header=None)
hdr = ms.index[ms[0] == "Board"][0]
ov = ms.iloc[hdr + 1:hdr + 1 + 42, :7]
ov.columns = ["Board", "Year", "Appeared", "Passed", "Pass %", "Notes", "Published"]
ov = ov[ov["Year"].isin([2024, 2025, 2026])].copy()
ov["Board"] = ov["Board"].replace(BOARD_ALIAS)
for c in ["Year", "Appeared", "Passed", "Pass %", "Published"]:
    ov[c] = num(ov[c])
ov["Pass %age"] = ov["Passed"] / ov["Appeared"]
overall = ov[["Board", "Year", "Appeared", "Passed", "Pass %age", "Published", "Notes"]].reset_index(drop=True)

# ---------------------------------------------------------------- Abbottabad
b = "Abbottabad"
d = sheet("Abb-Group-wise")
generic(b, d, "Year", "Appeared", "Passed", gender="Gender", category="Candidate Type",
        group="Group", grades=["A1", "A", "B", "C", "D", "E"])
d = sheet("Abb-Subject-wise")
push("subject", b, d["Year"], "Subject", d["Subject"], d["Appeared"], d["Passed"])

# --------------------------------------------------------------- Bahawalpur
b = "Bahawalpur"
for y in (2024, 2025, 2026):
    g = sheet(f"BWP {y} Grand Total")
    g.columns = ["Group", "Gender", "Appeared", "Passed", "Pass %"] + GRADES
    g["Year"] = y
    det = g[(g["Gender"].isin(["Male", "Female"])) & (g["Group"] != "Total")]
    generic(b, det, "Year", "Appeared", "Passed", gender="Gender", group="Group", grades=GRADES)
    for nm, cat in ((f"BWP {y} Total (Regular)", "Regular"), (f"BWP {y} Private", "Private")):
        c = sheet(nm)
        c.columns = ["Group", "Gender", "Appeared", "Passed", "Pass %"] + GRADES
        c = c[(c["Gender"] == "Total") & (c["Group"] != "Total")]
        push("category", b, [y], "Category", [cat], [num(c["Appeared"]).sum()], [num(c["Passed"]).sum()])
    s = sheet(f"BWP {y} Subject Wise Pass %")
    push("subject", b, s["Year"], "Subject", s[col(s, "subject")], s["Appeared"], s["Passed"])
d = sheet("BWP 2024 District Wise Pass %")
d = d[(num(d["Year"]) == 2024) & (d["District"] != "Total")]
push("district", b, d["Year"], "District", d["District"], d["Total Appeared"], d["Total Passed"])

# ------------------------------------------------------------------- Bannu
b = "Bannu"
d = sheet("BNU Group-wise")
d = d[(d["Part"] == "Part-II (2nd Year)") & (d["Row Type"] == "Detail")]
generic(b, d, "Year", "Appeared", "Passed", group="Group")
d = sheet("BNU 2026 Category-wise")
d = d[(d["Part"].str.contains("Part-II")) & (~d["Category"].isin(["Sub Total", "G. Total"]))]
generic(b, d, "Year", "Appeared", "Passed", gender="Category", category="Category")

# --------------------------------------------------------------------- DGK
b = "DGK"
d = sheet("DGK-Gender-wise")
generic(b, d, "Year", "Appeared", "Passed", gender="Gender")
d = sheet("DGK-Group-wise")
d = d[~d["Group"].isin(["Total", "Grand Total"])]
generic(b, d[(d["Candidate Type"].isin(["Regular", "Private"])) & (d["Gender"] == "Total")], "Year", "Appeared", "Passed", group="Group")
generic(b, d[(d["Candidate Type"].isin(["Regular", "Private"])) & (d["Gender"] == "Total")], "Year", "Appeared", "Passed",
        category="Candidate Type")
d = sheet("DGK-District-wise")
push("district", b, d["Year"], "District", d["District"], d["Appeared"], d["Passed"])
for nm, yrs in (("DGK-Subject-wise", [2024]), ("DGK-Subject-wise 2025", [2025])):
    s = sheet(nm)
    for y in yrs:
        a = s[col(s, str(y), "appeared")] if any(f"{y} appeared" in c.lower() for c in s.columns) else s[col(s, str(y), "applied")]
        t = pd.DataFrame({"Subject": s["Subject"], "A": num(a), "P": num(s[col(s, str(y), "passed")])})
        t = t.dropna().groupby("Subject").sum().reset_index()
        push("subject", b, y, "Subject", t["Subject"], t["A"], t["P"])
s = sheet("DGK-Subject-wise 2026")
t = pd.DataFrame({"Subject": s["Subject"], "A": num(s["2026 Appeared"]), "P": num(s["2026 Passed"])}).dropna()
t = t.groupby("Subject").sum().reset_index()
push("subject", b, 2026, "Subject", t["Subject"], t["A"], t["P"])

# --------------------------------------------------------------------- FSD
b = "FSD"
d = sheet("FSD Overall Grade-wise", 0)
d = d[d["Row_Type"] == "Detail"]
generic(b, d, "Year", "Appeared", "Pass", category="Candidate_Type", group="Group", grades=GRADES)
gs = []
for nm in ("FSD Regular Gender-School", "FSD Private Gender"):
    gs.append(sheet(nm, 0))
gs = pd.concat(gs)
gs = gs[gs["Row_Type"] == "Detail"]
generic(b, gs, "Year", "Appeared", "Pass", gender="Gender")
ds = pd.concat([sheet("FSD Regular District-Group", 0), sheet("FSD Private District-Group", 0)])
ds = ds[ds["Row_Type"] == "District Total"]
t = ds.assign(A=num(ds["Appeared"]), P=num(ds["Pass"])).groupby(["Year", "District"])[["A", "P"]].sum().reset_index()
push("district", b, t["Year"], "District", t["District"], t["A"], t["P"])
s = sheet("FSD Subjects", 0)
s = s[s["Part"].astype(str).str.contains("2")]
t = s.assign(A=num(s["Appear"]), P=num(s["Pass"])).groupby(["Year", "Subject_Name"])[["A", "P"]].sum().reset_index()
push("subject", b, t["Year"], "Subject", t["Subject_Name"], t["A"], t["P"])

# ------------------------------------------------------------------- FBISE
b = "FBISE"
d = sheet("FBISE Regional Details", 0)
d = d[(d["Area"] == "All Areas") & (d["Row_Type"] == "Detail") & (d["Gender"].isin(["Male", "Female"]))]
generic(b, d, "Year", "Appeared", "Pass", gender="Gender", category="Candidate_Type", group="Group",
        grades=["A1", "A", "B", "C", "D", "E"])
# provincial split of FBISE candidates (extra detail)
# --------------------------------------------------------------- Gujranwala
b = "Gujranwala"
for y in (2024, 2025):
    for grp in ("Pre-Medical", "Pre-Engineering", "Humanities", "General Science", "Commerce", "Home Economics"):
        d = sheet(f"GRW {y} {grp} Stats")
        d = d[d["Category"].isin(["Regular Male", "Regular Female", "Private Male", "Private Female"])].copy()
        d["Year"], d["Grp"] = y, grp
        generic(b, d, "Year", "Appeared", "Pass", gender="Category", category="Category", group="Grp", grades=GRADES)
    d = sheet(f"GRW {y} District-wise Stats")
    d = d[d["District"] != "Total"]
    push("district", b, y, "District", d["District"], d["Total Appeared"], d["Total Pass"])
    s = sheet(f"GRW {y} Subject Pass % Part-II")
    push("subject", b, y, "Subject", s["Subject Name"], s["Appeared"], s["Pass"])

# ------------------------------------------------------------------- Kohat
b = "Kohat"
d = sheet("KOH Group-wise")
d = d[(d["Part"] == "Part-II (2nd Year)") & (d["Row Type"] == "Detail")]
generic(b, d, "Year", "Appeared", "Passed", gender="Category", category="Category", group="Group",
        grades=["A-1", "A", "B", "C", "D", "E"])
s = sheet("KOH Subject-wise")
s = s[s["Part"].astype(str).str.contains("Part-II")]
push("subject", b, s["Year"], "Subject", s["Subject"], s["Appeared"], s["Passed"])

# ------------------------------------------------------------------ Lahore
b = "Lahore"
for y in (2024, 2025, 2026):
    d = sheet(f"LHR {y} Statistical Data")
    d = d[(d["Gender"].isin(["Boys", "Girls"])) & (d["Category"].isin(["Reg (Govt. Inst.)", "Reg (Pvt. Inst.)", "Private"]))
          & (~d["Group"].astype(str).str.contains("All Groups"))].copy()
    d["Year"] = y
    d = d.rename(columns={"A+ Passed": "gA+", "A Passed": "gA", "B Passed": "gB", "C Passed": "gC",
                          "D Passed": "gD", "E Passed": "gE"})
    generic(b, d, "Year", "Appeared", "Passed", gender="Gender", category="Category", group="Group",
            grades=["gA+", "gA", "gB", "gC", "gD", "gE"])
    s = sheet(f"LHR {y} Subject Wise Pass %")
    t = s.assign(A=num(s["Overall Appeared"]), P=num(s["Overall Passed"]))
    t = t.groupby(t[col(s, "subject")])[["A", "P"]].sum().reset_index()
    push("subject", b, y, "Subject", t.iloc[:, 0], t["A"], t["P"])
d = sheet("LHR 2026 District Wise Pass %")
d = d[~d["Group"].astype(str).str.lower().str.contains("total|all|gender")]
d = d[d["Gender"].isin(["Boys", "Girls"])]
t = d.assign(A=num(d["Total Appeared"]), P=num(d["Total Passed"])).groupby("District")[["A", "P"]].sum().reset_index()
push("district", b, 2026, "District", t["District"], t["A"], t["P"])

# ------------------------------------------------------------------ Mardan
b = "Mardan"
for nm, grp in (("Pre-Medical", "Pre-Medical"), ("Pre-Engineering", "Pre-Engineering"),
                ("General Science", "General Science"), ("Humanities", "Humanities"),
                ("Home Economics", "Home Economics")):
    d = sheet(f"Mar-{nm} Group")
    d = d[d["Category"] != "Total"].copy()
    d["Grp"] = grp
    generic(b, d, "Year", "Appeared", "Passed", gender="Category", category="Category", group="Grp")

# ---------------------------------------------------------------- Peshawar
b = "Peshawar"
d = sheet("Pes-Group-wise Part-II")
generic(b, d, "Year", "Total Students", "Passed", gender="Category", category="Category", group="Group",
        grades=["A1", "A", "B", "C", "D", "E"])
s = sheet("Pes-Subject-wise Pass %")
push("subject", b, s["Year"], "Subject", s["Subject"], s["Appeared"], s["Passed"])

# -------------------------------------------------------------- Rawalpindi
b = "Rawalpindi"
d = sheet("RWP Pass % by Category", 0)
generic(b, d[(d["Candidate_Type"] == "Overall") & (d["Gender"].isin(["Male", "Female"]))], "Year", "Candidates", "Pass", gender="Gender")
generic(b, d[(d["Candidate_Type"].isin(["Regular", "Private"])) & (d["Gender"] == "Total")], "Year", "Candidates", "Pass",
        category="Candidate_Type")
generic(b, d[(d["Candidate_Type"] == "Overall") & (d["Gender"] == "Total")], "Year", "Candidates", "Pass", group="Group")
o = sheet("RWP Overview Summary", 0)
push_grades(b, None, o[["Year"] + GRADES])
d = sheet("RWP District Wise Performance", 0)
d = d[d["Row_Type"] == "Detail"]
push("district", b, d["Year"], "District", d["District"], d["Total_Appeared"], d["Total_Passed"])
s = sheet("RWP Subject Wise Pass %", 0)
s = s[s["Part"].astype(str).str.contains("2")]
push("subject", b, s["Year"], "Subject", s["Subject"], s["Appeared"], s["Passed"])

# ----------------------------------------------------------------- Sahiwal
b = "Sahiwal"
d = sheet("SWL Pass Percentage")
d = d[~d["Group"].str.contains("TOTAL")]
generic(b, d[(d["Category"] == "OVERALL") & (d["Gender"].isin(["Male", "Female"]))], "Year", "Appeared", "Pass", gender="Gender")
generic(b, d[(d["Category"].isin(["REGULAR", "PRIVATE"])) & (d["Gender"] == "Total")], "Year", "Appeared", "Pass", category="Category")
generic(b, d[(d["Category"] == "OVERALL") & (d["Gender"] == "Total")], "Year", "Appeared", "Pass", group="Group")
d = sheet("SWL District Pass %")
t = d.assign(A=num(d["Total Appeared"]), P=num(d["Total Pass"])).groupby(["Year", "District"])[["A", "P"]].sum().reset_index()
t["District"] = t["District"].str.title()
push("district", b, t["Year"], "District", t["District"], t["A"], t["P"])
s = sheet("SWL Subjectwise Pass %")
push("subject", b, s["Year"], "Subject", s["Subject Name"], s["Overall Appeared"], s["Overall Pass"])

# ---------------------------------------------------------------- Sargodha
b = "Sargodha"
d = sheet("Sar-Group-wise")
d = d[~d["Group"].str.upper().eq("TOTAL")]
generic(b, d[(d["Student Type"] == "Overall") & (d["Gender"].isin(["Male", "Female"]))], "Year", "Appeared", "Passed", gender="Gender")
generic(b, d[(d["Student Type"].isin(["Regular", "Private"])) & (d["Gender"] == "Total")], "Year", "Appeared", "Passed",
        category="Student Type")
generic(b, d[(d["Student Type"] == "Overall") & (d["Gender"] == "Total")], "Year", "Appeared", "Passed", group="Group")
d = sheet("Sar-District-wise")
d = d[(d["District"] != "Overall") & (d["Category"] == "Total")]
push("district", b, d["Year"], "District", d["District"], d["Appeared"], d["Passed"])
d = sheet("Sar-Grade Dist. by District")
d = d[(d["District"] == "Overall") & (d["Category"] == "Total")]
push_grades(b, None, d[["Year"] + GRADES])

# -------------------------------------------------------------------- Swat
b = "Swat"
d = sheet("Swat-Group-wise Distribution")
d = d[(d["Exam Class"] == "12th") & (~d["Category"].isin(["Sub Total", "Grand Total"])) & (d["Group"] != "All Groups")]
d = d.rename(columns={"A-I": "A1"})
generic(b, d, "Year", "Appeared", "Passed", gender="Category", category="Category", group="Group",
        grades=["A1", "A", "B", "C", "D", "E"])
s = sheet("Swat-Subject-wise Pass %")
s = s[~s["Class"].astype(str).str.contains("11")]
t = s.assign(A=num(s["Appeared"]), P=num(s["Passed"])).groupby(["Year", "Subject"])[["A", "P"]].sum().reset_index()
push("subject", b, t["Year"], "Subject", t["Subject"], t["A"], t["P"])


# ------------------------------------------------------------------ write
def finish(kind):
    df = pd.concat(R[kind], ignore_index=True)
    keycols = [c for c in df.columns if c not in ("Appeared", "Passed", "Count")]
    val = [c for c in ("Appeared", "Passed", "Count") if c in df.columns]
    df = df.dropna(subset=["Year"]).groupby(keycols, dropna=False)[val].sum(min_count=1).reset_index()
    if "Appeared" in df.columns:
        df = df[(df["Appeared"].fillna(0) > 0) | (df["Passed"].fillna(0) > 0)]
    return df.sort_values(keycols).reset_index(drop=True)


overall.to_csv(OUT / "overall.csv", index=False)
for k in R:
    t = finish(k)
    t["Year"] = t["Year"].astype(int)
    t.to_csv(OUT / f"{k}.csv", index=False)
    print(f"{k:9s} rows={len(t):5d} boards={t['Board'].nunique():2d}")
print("overall   rows=%d" % len(overall))