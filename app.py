# app.py
import re
from typing import Dict, List
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------
# App config
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="NGSS Toolkit (Skills & Standards)",
    page_icon="🔧",
    layout="wide",
)

# ---------------------------------------------------------------------
# Header mapping (aliases → canonical column names)
# Add more aliases if your CSVs use different headers.
# ---------------------------------------------------------------------
ALIAS_MAP: Dict[str, List[str]] = {
    "grade":    ["grade", "gr", "g", "Grade"],
    "practice": ["practice", "ngss_practice", "skill", "skills_practice", "Practice"],
    # Standards-ish columns (optional)
    "code":     ["code", "ngss", "id", "pe_code", "pe", "PE Code"],
    "title":    ["title", "statement", "performance_expectation", "pe_statement",
                 "Performance Expectation", "PE Statement"],
    "domain":   ["domain", "topic", "disciplinary_core_idea", "dci_domain", "Domain"],
    "dci":      ["dci", "disciplinary_core_idea", "core_idea", "DCI"],
    "sep":      ["sep", "science_and_engineering_practices", "practice_sep", "SEP"],
    "ccc":      ["ccc", "crosscutting_concepts", "crosscutting", "CCC"],
    "notes":    ["notes", "description", "comment", "Notes", "Description"],
    # Practices Map columns (A0..A6). Only the ones present will be shown.
    "a0": ["a0", "A0"], "a1": ["a1", "A1"], "a2": ["a2", "A2"],
    "a3": ["a3", "A3"], "a4": ["a4", "A4"], "a5": ["a5", "A5"], "a6": ["a6", "A6"],
}

PREFERRED_COL_ORDER = ["grade","practice","code","title","domain","dci","sep","ccc","notes",
                       "a0","a1","a2","a3","a4","a5","a6"]

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def _normalize_header(h: str) -> str:
    """lowercase, replace non-alnum with underscores, collapse repeats"""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower())).strip("_")

def canonicalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    # build map from original → canonical
    mapping = {}
    for col in df.columns:
        norm = _normalize_header(col)
        mapped = None
        for canon, variants in ALIAS_MAP.items():
            if norm in [v.lower() for v in variants]:
                mapped = canon
                break
        mapping[col] = mapped or norm
    out = df.rename(columns=mapping)

    # Ensure grade column exists so filters work
    if "grade" not in out.columns:
        out["grade"] = ""

    # reorder columns: preferred first, keep the rest
    ordered = [c for c in PREFERRED_COL_ORDER if c in out.columns]
    remaining = [c for c in out.columns if c not in ordered]
    return out[ordered + remaining]

def add_grade_if_missing(df: pd.DataFrame, grade_value: str) -> pd.DataFrame:
    if not grade_value:
        return df
    out = df.copy()
    out["grade"] = out["grade"].fillna("").astype(str)
    needs = out["grade"].str.strip() == ""
    out.loc[needs, "grade"] = str(grade_value)
    return out

def filter_contains(df: pd.DataFrame, search: str, col_filters: Dict[str,str]) -> pd.DataFrame:
    out = df.copy()
    if search:
        s = search.lower()
        mask = pd.Series(False, index=out.index)
        for col in out.columns:
            mask |= out[col].astype(str).str.lower().str.contains(s, na=False)
        out = out[mask]
    for col, val in (col_filters or {}).items():
        if val:
            out = out[out[col].astype(str).str.lower().str.contains(val.lower(), na=False)]
    return out

def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

# ---------------------------------------------------------------------
# SKILLS (Practices Map) view
# ---------------------------------------------------------------------
_GRADE_ORDER = ["4th","5th","6th","7th","8th","9th","10th","11th","12th","K","1st","2nd","3rd"]
def _grade_sort_key(g: str) -> int:
    g = str(g).strip()
    if g in _GRADE_ORDER:
        return _GRADE_ORDER.index(g)
    m = re.search(r"\d+", g)
    return 999 if not m else 100 + int(m.group())

def render_skills_view(df: pd.DataFrame) -> None:
    """Practice selector, grade chips, A0..A6 columns.
       If 'practice' col is missing, fall back to __source__ (CSV filename)."""
    st.title("NGSS Toolkit — Skills")
    st.caption("Select a practice and see which assignments address it, by grade.")

    # Build practice options
    practice_col = None
    practice_vals = []

    if "practice" in df.columns and df["practice"].astype(str).str.strip().ne("").any():
        practice_col = "practice"
        practice_vals = sorted(df["practice"].dropna().astype(str).unique())
    elif "__source__" in df.columns:
        practice_col = "__source__"
        # Nicify file names: strip extension, replace dashes/underscores
        def pretty(x: str) -> str:
            import os, re
            base = os.path.splitext(os.path.basename(str(x)))[0]
            base = re.sub(r"[_-]+", " ", base).strip()
            return base
        # Make a map so we show nice labels but filter by exact source value
        sources = df["__source__"].dropna().astype(str).unique()
        practice_vals = sorted([pretty(s) for s in sources])
        source_map = {pretty(s): s for s in sources}
    else:
        practice_vals = ["All"]  # last resort

    left, right = st.columns([2, 3])
    selected = left.selectbox("NGSS Practice", ["All"] + practice_vals, index=0)

    # Grade chips
    all_grades = sorted([str(x) for x in df.get("grade", pd.Series([])).dropna().unique()],
                        key=_grade_sort_key)
    default_grades = [g for g in _GRADE_ORDER if g in all_grades] or all_grades
    chosen_grades = right.multiselect("Grades to include", options=all_grades, default=default_grades)

    # Filter
    work = df.copy()
    if selected != "All" and practice_col:
        if practice_col == "__source__":
            work = work[work["__source__"].astype(str) == source_map[selected]]
        else:
            work = work[work["practice"].astype(str) == selected]
    if chosen_grades:
        work = work[work["grade"].astype(str).isin(chosen_grades)]

    # Build grid
    grid_cols = ["grade"] + [c for c in ["a0","a1","a2","a3","a4","a5","a6"] if c in work.columns]
    if "grade" not in work.columns or len(grid_cols) == 1:
        st.warning("I don’t see the expected columns for the Skills view. "
                   "Your CSV should include `grade` and some of `A0…A6`.")
        st.dataframe(work, use_container_width=True, hide_index=True)
        return

    work = work[grid_cols].copy()
    work["__ord__"] = work["grade"].map(_grade_sort_key)
    work = work.sort_values("__ord__").drop(columns="__ord__")
    headers = {c: c.upper() if c.startswith("a") else c.capitalize() for c in grid_cols}
    work = work.rename(columns=headers)

    heading = selected if selected != "All" else "All"
    st.markdown(f"### NGSS — {heading}")
    st.dataframe(work, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# STANDARDS (table) view
# ---------------------------------------------------------------------
def render_standards_view(df: pd.DataFrame) -> None:
    st.title("NGSS Toolkit — Standards")
    st.caption("Upload CSVs, search/filter, show/hide columns, and export the filtered view.")

    c1, c2, c3, c4 = st.columns([2,2,2,1])
    search = c1.text_input("Search across all fields", "")
    grade_filter = c2.multiselect("Filter grades",
                                  sorted([g for g in df.get('grade', pd.Series([])).astype(str).unique() if g]),
                                  default=[])
    sort_col = c3.selectbox("Sort by", options=list(df.columns), index=0)
    sort_dir = c4.selectbox("Direction", ["asc","desc"], index=0)

    with st.expander("Column filters (contains match)"):
        fcols = st.multiselect("Choose columns to filter", options=list(df.columns))
        col_filters = {}
        if fcols:
            for c in fcols:
                col_filters[c] = st.text_input(f"Filter value for `{c}`", key=f"filter_{c}")

    work = df.copy()
    if grade_filter:
        work = work[work["grade"].astype(str).isin(grade_filter)]
    work = filter_contains(work, search, col_filters)
    work = work.sort_values(by=sort_col, ascending=(sort_dir == "asc"), kind="stable")

    with st.expander("Show / hide columns"):
        cols_visible = st.multiselect("Columns", options=list(work.columns), default=list(work.columns))
        work = work[cols_visible]

    st.write(f"**{len(work):,}** rows matched.")
    st.dataframe(work, use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered CSV",
        data=csv_bytes(work),
        file_name="ngss_standards_filtered.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------
# Session state for datasets
# ---------------------------------------------------------------------
if "skills_df" not in st.session_state:
    st.session_state.skills_df = pd.DataFrame()
if "standards_df" not in st.session_state:
    st.session_state.standards_df = pd.DataFrame()

# ---------------------------------------------------------------------
# Sidebar — mode + data ingest
# ---------------------------------------------------------------------
st.sidebar.title("NGSS Toolkit")
mode = st.sidebar.radio("View", ["Skills", "Standards"], horizontal=True)

with st.sidebar.expander("Upload CSV(s)", expanded=True):
    uploaded = st.file_uploader("Choose one or more CSV files", type=["csv"], accept_multiple_files=True)
    default_grade = st.selectbox("Assign grade (used when missing in CSV)", ["", "4th","5th","6th","7th","8th","9th","10th","11th","12th","K","1st","2nd","3rd"], index=0)
    if st.button("Add to dataset"):
        frames = []
        for file in uploaded or []:
            df = pd.read_csv(file)
            df = canonicalize_headers(df)
            df = add_grade_if_missing(df, default_grade)
            frames.append(df)
        if frames:
            new_df = pd.concat(frames, ignore_index=True)
            if mode == "Skills":
                st.session_state.skills_df = pd.concat([st.session_state.skills_df, new_df], ignore_index=True)
            else:
                st.session_state.standards_df = pd.concat([st.session_state.standards_df, new_df], ignore_index=True)
            st.success(f"Added {sum(len(f) for f in frames):,} rows to {mode}.")

with st.sidebar.expander("Load CSVs from /data"):
    import glob, os
    if st.button("Load /data into current view"):
        paths = glob.glob("data/*.csv")
        if not paths:
            st.info("No CSV files found in /data. Commit some later.")
        frames = []
        for p in paths:
            try:
                df = pd.read_csv(p)
                df = canonicalize_headers(df)
                frames.append(df)
            except Exception as e:
                st.warning(f"Could not read {os.path.basename(p)}: {e}")
        if frames:
            loaded = pd.concat(frames, ignore_index=True)
            if mode == "Skills":
                st.session_state.skills_df = pd.concat([st.session_state.skills_df, loaded], ignore_index=True)
            else:
                st.session_state.standards_df = pd.concat([st.session_state.standards_df, loaded], ignore_index=True)
            st.success(f"Loaded {len(loaded):,} rows from /data into {mode}.")

if st.sidebar.button("Clear current dataset"):
    if mode == "Skills":
        st.session_state.skills_df = pd.DataFrame()
    else:
        st.session_state.standards_df = pd.DataFrame()
    st.toast(f"Cleared {mode} dataset")

# ---------------------------------------------------------------------
# Main routing
# ---------------------------------------------------------------------
df = st.session_state.skills_df if mode == "Skills" else st.session_state.standards_df

if df.empty:
    st.title(f"NGSS Toolkit — {mode}")
    st.info("No rows yet. Use the sidebar to upload CSVs or load from `/data`.")
else:
    if mode == "Skills":
        render_skills_view(df)
        st.markdown("---")
        st.caption("Columns A0–A6 come directly from your CSV headers; only present columns are shown.")
    else:
        render_standards_view(df)
