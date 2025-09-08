# app.py
import os
import re
from typing import Dict, List
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# App config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NGSS Toolkit (Skills & Standards)", page_icon="🔧", layout="wide")

# Make sidebar narrower + tighten page padding
st.markdown("""
<style>
  /* Sidebar width */
  [data-testid="stSidebar"] {
    width: 200px;           /* ← change to 220/260/etc if you like */
    min-width: 240px;
  }

  /* Give the main content more room by trimming default padding */
  .block-container {
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
  }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS (Skills view uses the SAME CSVs/behavior as your previous app)
# ──────────────────────────────────────────────────────────────────────────────
DATA_DIR = "data"

PRACTICES = {
    "NGSS 1 — Asking questions & defining problems": {
        "key": "ngss1",
        "file": "NGSS1_Asking_Questions.csv",
        "desc": "Practice 1"
    },
    "NGSS 2 — Developing & using models": {
        "key": "ngss2",
        "file": "NGSS_2_Developing_and_Using_Models.csv",
        "desc": "Practice 2"
    },
    "NGSS 3 — Planning & carrying out investigations": {
        "key": "ngss3",
        "file": "NGSS3_Planning_Investigations.csv",
        "desc": "Practice 3"
    },
    "NGSS 4 — Analyzing & interpreting data": {
        "key": "ngss4",
        "file": "NGSS_4_Analyzing_and_Interpreting_Data.csv",
        "desc": "Practice 4"
    },
    "NGSS 5 — Using mathematical & computational thinking": {
        "key": "ngss5",
        "file": "NGSS_5_Using_Mathematical_and_Computational_Thinking.csv",
        "desc": "Practice 5"
    },
}
ASSIGNMENT_COLUMNS = ["A0", "A1", "A2", "A3", "A4", "A5", "A6"]
GRADE_ORDER = ["4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th"]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers shared
# ──────────────────────────────────────────────────────────────────────────────
def _normalize_header(h: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower())).strip("_")

def filter_contains(df: pd.DataFrame, search: str, col_filters: Dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    if search:
        s = search.lower()
        m = pd.Series(False, index=out.index)
        for c in out.columns:
            m |= out[c].astype(str).str.lower().str.contains(s, na=False)
        out = out[m]
    for c, v in (col_filters or {}).items():
        if v:
            out = out[out[c].astype(str).str.lower().str.contains(v.lower(), na=False)]
    return out

def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

# ──────────────────────────────────────────────────────────────────────────────
# SKILLS VIEW  — EXACTLY your previous app’s behavior/UI
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_practice_df(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path, dtype=str).fillna("-")
    cols = ["Grade"] + [c for c in ASSIGNMENT_COLUMNS if c in df.columns]
    df = df[[c for c in cols if c in df.columns]]
    df["__order"] = df["Grade"].apply(lambda g: GRADE_ORDER.index(g) if g in GRADE_ORDER else 999)
    df = df.sort_values("__order").drop(columns="__order")
    return df

def md_cell(text: str) -> str:
    if not isinstance(text, str) or text.strip() in ("", "-"):
        return "<span style='color:#9ca3af;'>–</span>"
    html = text.replace("\r\n", "\n").replace("\r", "\n").strip().replace("\n", "<br>")
    return html

def render_table_html(df: pd.DataFrame) -> str:
    for col in ASSIGNMENT_COLUMNS:
        if col not in df.columns:
            df[col] = "-"
    df = df[["Grade"] + ASSIGNMENT_COLUMNS]

    thead = (
        "<thead><tr>"
        "<th style='position:sticky;left:0;z-index:2;background:#f9fafb;border-right:1px solid #e5e7eb;'>Grade</th>"
        + "".join(f"<th>{col}</th>" for col in ASSIGNMENT_COLUMNS)
        + "</tr></thead>"
    )

    body_rows = []
    for _, row in df.iterrows():
        cells = []
        grade_html = f"<td style='position:sticky;left:0;z-index:1;background:#fff;border-right:1px solid #e5e7eb;font-weight:600;'>{row['Grade']}</td>"
        cells.append(grade_html)
        for col in ASSIGNMENT_COLUMNS:
            content = md_cell(row[col]).replace("**", "")
            cell_html = "<div style='line-height:1.25;'>"
            first = content.split("<br>")[0] if "<br>" in content else content
            cell_html += f"<div style='font-weight:600;text-decoration:underline;margin-bottom:0.25rem;'>{first}</div>"
            if "<br>" in content:
                parts = content.split("<br>")[1:]
                bullets = []
                for ln in parts:
                    s = ln.strip()
                    if s in ("", "–"):
                        continue
                    if s.startswith("•"):
                        bullets.append(f"<li>{s[1:].strip()}</li>")
                    elif s.startswith("- "):
                        bullets.append(f"<li>{s[2:].strip()}</li>")
                    else:
                        bullets.append(f"<li>{s}</li>")
                if bullets:
                    cell_html += f"<ul style='margin:0 0 0.25rem 1rem;padding:0;'>{''.join(bullets)}</ul>"
            cell_html += "</div>"
            cells.append(f"<td>{cell_html}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    tbody = "<tbody>" + "".join(body_rows) + "</tbody>"

    return f"""
    <div style="overflow:auto; border:1px solid #e5e7eb; border-radius:12px; max-height:80vh;">
      <table style="
            border-collapse:separate;
            border-spacing:0;
            width:100%;
            min-width:1100px;   /* allow more width */
            table-layout:fixed;
            font-size:14px;     /* slightly smaller font */
      ">
        <style>
          table th, table td {{
            border-bottom:1px solid #e5e7eb;
            vertical-align:top;
            padding:6px 8px;   /* more compact cells */
            word-wrap:break-word;
            overflow-wrap:break-word;
            white-space:normal;
          }}
          thead th {{
            position:sticky; top:0; z-index:1;
            background:#f9fafb;
            font-weight:600;
            text-align:left;
          }}
        </style>
        {thead}
        {tbody}
      </table>
    </div>
    """
def render_skills() -> None:
    st.markdown(
        "<h1 style='margin-bottom:0.25rem;'>NGSS Practices Map (K–12 Prototype)</h1>"
        "<div style='color:#6b7280;margin-bottom:1rem;'>Select a practice and see which assignments address it, by grade.</div>",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown("### Choose NGSS Practice")
        practice_label = st.selectbox("Practice", list(PRACTICES.keys()), index=0)
        st.markdown("---")
        st.markdown("### Filter Grades")
        selected_grades = st.multiselect("Grades to include", options=GRADE_ORDER, default=GRADE_ORDER)
        st.markdown("---")
        st.caption("This view shows which assignments (A0–A6) address each NGSS practice. "
                   "Cells show the unit title (bold/underlined) and activities as bullets.")

    meta = PRACTICES[practice_label]
    df = load_practice_df(meta["file"])
    if selected_grades:
        df = df[df["Grade"].isin(selected_grades)]
    else:
        st.info("No grades selected. Choose at least one grade in the sidebar.")
        return

    st.markdown(f"<h3 style='margin:0.25rem 0 0.5rem 0;'>{practice_label}</h3>", unsafe_allow_html=True)
    st.markdown(render_table_html(df), unsafe_allow_html=True)

    st.download_button(
        label="Download this view as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{meta['key']}_filtered_view.csv",
        mime="text/csv",
    )

# ──────────────────────────────────────────────────────────────────────────────
# STANDARDS VIEW  — searchable/filterable table (same as before)
# ──────────────────────────────────────────────────────────────────────────────
ALIAS_MAP: Dict[str, List[str]] = {
    "grade": ["grade", "gr", "g", "Grade"],
    "code":  ["code", "ngss", "id", "pe_code", "pe", "PE Code"],
    "title": ["title", "statement", "performance_expectation", "pe_statement", "Performance Expectation"],
    "domain":["domain", "topic", "disciplinary_core_idea", "dci_domain"],
    "dci":   ["dci", "disciplinary_core_idea", "core_idea"],
    "sep":   ["sep", "science_and_engineering_practices"],
    "ccc":   ["ccc", "crosscutting_concepts"],
    "notes": ["notes", "description", "comment"],
}
PREFERRED_ORDER = ["grade","code","title","domain","dci","sep","ccc","notes"]

def canonicalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for col in df.columns:
        norm = _normalize_header(col)
        mapped = None
        for canon, variants in ALIAS_MAP.items():
            if norm in [v.lower() for v in variants]:
                mapped = canon; break
        mapping[col] = mapped or norm
    out = df.rename(columns=mapping)
    if "grade" not in out.columns: out["grade"] = ""
    ordered = [c for c in PREFERRED_ORDER if c in out.columns]
    remaining = [c for c in out.columns if c not in ordered]
    return out[ordered + remaining]

def add_grade_if_missing(df: pd.DataFrame, grade_value: str) -> pd.DataFrame:
    if not grade_value: return df
    out = df.copy()
    out["grade"] = out["grade"].fillna("").astype(str)
    needs = out["grade"].str.strip() == ""
    out.loc[needs, "grade"] = str(grade_value)
    return out

def render_standards() -> None:
    st.title("NGSS Toolkit — Standards")
    st.caption("Upload CSVs, search/filter, show/hide columns, and export the filtered view.")

    df = st.session_state.get("standards_df", pd.DataFrame())
    if df.empty:
        st.info("No rows yet. Use the sidebar to upload CSVs or load from `/data`.")
        return

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
    st.download_button("Download filtered CSV", data=csv_bytes(work),
                       file_name="ngss_standards_filtered.csv", mime="text/csv")

# ──────────────────────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────────────────────
if "standards_df" not in st.session_state:
    st.session_state.standards_df = pd.DataFrame()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar: mode + per-mode controls
# ──────────────────────────────────────────────────────────────────────────────
mode = st.sidebar.radio("View", ["Skills", "Standards"], horizontal=True)

if mode == "Standards":
    with st.sidebar.expander("Upload CSV(s)", expanded=True):
        uploaded = st.file_uploader("Choose one or more CSV files", type=["csv"], accept_multiple_files=True)
        default_grade = st.selectbox("Assign grade (used when missing in CSV)",
                                     ["","4th","5th","6th","7th","8th","9th","10th","11th"], index=0)
        if st.button("Add to Standards dataset"):
            frames = []
            for file in uploaded or []:
                df = pd.read_csv(file)
                df = canonicalize_headers(df)
                df = add_grade_if_missing(df, default_grade)
                frames.append(df)
            if frames:
                new_df = pd.concat(frames, ignore_index=True)
                st.session_state.standards_df = pd.concat([st.session_state.standards_df, new_df], ignore_index=True)
                st.success(f"Added {sum(len(f) for f in frames):,} rows.")

    with st.sidebar.expander("Load CSVs from /data"):
        import glob
        if st.button("Load /data into Standards"):
            paths = glob.glob(os.path.join(DATA_DIR, "*.csv"))
            if not paths:
                st.info("No CSV files found in /data.")
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
                st.session_state.standards_df = pd.concat([st.session_state.standards_df, loaded], ignore_index=True)
                st.success(f"Loaded {len(loaded):,} rows from /data.")

    if st.sidebar.button("Clear Standards dataset"):
        st.session_state.standards_df = pd.DataFrame()
        st.toast("Cleared Standards dataset")

# ──────────────────────────────────────────────────────────────────────────────
# Route
# ──────────────────────────────────────────────────────────────────────────────
if mode == "Skills":
    render_skills()
else:
    render_standards()
