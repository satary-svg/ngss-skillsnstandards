# app.py
import io, re, time
from typing import Dict, List
import pandas as pd
import streamlit as st

st.set_page_config(page_title="NGSS Toolkit (Skills & Standards)", page_icon="🔧", layout="wide")

ALIAS_MAP: Dict[str, List[str]] = {
    "code": ["code", "ngss", "id", "pe_code", "pe"],
    "title": ["title", "statement", "performance_expectation", "pe_statement"],
    "domain": ["domain", "topic", "disciplinary_core_idea", "dci_domain"],
    "dci": ["dci", "disciplinary_core_idea", "core_idea"],
    "sep": ["sep", "science_and_engineering_practices", "practice"],
    "ccc": ["ccc", "crosscutting_concepts", "crosscutting"],
    "notes": ["notes", "description", "comment"],
    "grade": ["grade", "gr", "g"],
}
PREFERRED_COL_ORDER = ["grade","code","title","domain","dci","sep","ccc","notes"]

def normalize_header(h: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower())).strip("_")

def canonicalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for col in df.columns:
        norm = normalize_header(col)
        mapped = None
        for canon, variants in ALIAS_MAP.items():
            if norm in variants:
                mapped = canon
                break
        mapping[col] = mapped or norm
    out = df.rename(columns=mapping)
    if "grade" not in out.columns:
        out["grade"] = ""
    ordered = [c for c in PREFERRED_COL_ORDER if c in out.columns]
    remaining = [c for c in out.columns if c not in ordered]
    return out[ordered + remaining]

def add_grade(df: pd.DataFrame, grade_value: str) -> pd.DataFrame:
    if not grade_value:
        return df
    out = df.copy()
    out["grade"] = out["grade"].fillna("").astype(str)
    needs = out["grade"].str.strip() == ""
    out.loc[needs, "grade"] = str(grade_value)
    return out

def filter_df(df: pd.DataFrame, search: str, col_filters: Dict[str,str]) -> pd.DataFrame:
    out = df.copy()
    if search:
        mask = pd.Series(False, index=out.index)
        s = search.lower()
        for col in out.columns:
            mask |= out[col].astype(str).str.lower().str.contains(s, na=False)
        out = out[mask]
    for col, val in col_filters.items():
        if val:
            out = out[out[col].astype(str).str.lower().str.contains(val.lower(), na=False)]
    return out

def download_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

if "skills_df" not in st.session_state:
    st.session_state.skills_df = pd.DataFrame()
if "standards_df" not in st.session_state:
    st.session_state.standards_df = pd.DataFrame()

st.sidebar.title("NGSS Toolkit")
mode = st.sidebar.radio("View", ["Skills", "Standards"], horizontal=True)

with st.sidebar.expander("Upload CSV(s)", expanded=True):
    uploaded = st.file_uploader("Choose one or more CSV files", type=["csv"], accept_multiple_files=True)
    default_grade = st.selectbox("Assign grade (used when missing in CSV)", ["" ,"1","2","3","4","5"], index=0)
    if st.button("Add to dataset"):
        frames = []
        for file in uploaded or []:
            df = pd.read_csv(file)
            df = canonicalize_headers(df)
            df = add_grade(df, default_grade)
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

st.title(f"NGSS Toolkit — {mode}")
st.caption("Upload CSVs, search/filter, show/hide columns, and export the filtered view.")

df = st.session_state.skills_df if mode == "Skills" else st.session_state.standards_df

if df.empty:
    st.info("No rows yet. Use the sidebar to upload CSVs or load from `/data`.")
    st.stop()

col1, col2, col3, col4 = st.columns([2,2,2,1])
search = col1.text_input("Search across all fields", "")
grade_filter = col2.multiselect("Filter grades", sorted([g for g in df.get('grade', pd.Series([])).astype(str).unique() if g]), default=[])
sort_col = col3.selectbox("Sort by", options=list(df.columns), index=0)
sort_dir = col4.selectbox("Direction", ["asc","desc"], index=0)

with st.expander("Column filters (contains match)"):
    fcols = st.multiselect("Choose columns to filter", options=list(df.columns))
    col_filters = {}
    if fcols:
        for c in fcols:
            col_filters[c] = st.text_input(f"Filter value for `{c}`", key=f"filter_{c}")
    else:
        col_filters = {}

work = df.copy()
if grade_filter:
    work = work[work["grade"].astype(str).isin(grade_filter)]
work = filter_df(work, search, col_filters)
ascending = (sort_dir == "asc")
work = work.sort_values(by=sort_col, ascending=ascending, kind="stable")

with st.expander("Show / hide columns"):
    cols_visible = st.multiselect("Columns", options=list(work.columns), default=list(work.columns))
    work = work[cols_visible]

st.write(f"**{len(work):,}** rows matched.")
st.dataframe(work, use_container_width=True, hide_index=True)

st.download_button(
    "Download filtered CSV",
    data=download_csv_bytes(work),
    file_name=f"ngss_{mode.lower()}_filtered.csv",
    mime="text/csv",
)

st.markdown('---')
st.caption("Tip: Commit CSVs into the `/data` folder so the app can load them automatically on deploy.")
