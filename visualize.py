"""
JeilTechnos yard visualization for field and selected project-code-weight results.

This version reuses the old hand-drawn yard diagram style:
- A/B/C/D/E/F/G/H/I yards are drawn as fixed rectangles.
- Factory areas are drawn as the orange polygon used in the old visualizer.
- Default data comes from ../ProgramRun, using the same MES-valid 7,805-packing input.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import html

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

SCRIPT_DIR = Path(__file__).resolve().parent
PROGRAM_RUN_DIR = SCRIPT_DIR / "ProgramRun"
if not PROGRAM_RUN_DIR.exists():
    PROGRAM_RUN_DIR = SCRIPT_DIR.parent / "ProgramRun"
DAILY_PLACEMENT_FILE = "DailyPlacement.csv"
YARD_CONFIG_FILE = "YardInputWithStack.csv"
ASSIGN_RESULT_FILE = "AssignResult_jeil_newyard.csv"
FIELD_UTILIZATION_FILE = "JeilYardUtilization.csv"
JEIL_PROJECT_YARD_FILE = "JeilProjectYardUsage.csv"
FIELD_OBJECT_SUMMARY_FILE = "JeilFieldObjectSummary.csv"
BASE_DATE_STR = "2026-01-01"
FIELD_SOURCE_LABEL = "현업 (Jeil Technos)"

# All experiments use the same 7,805-packing comparison input.
V3_MIXING_WEIGHTS = [0, 500, 2000]

ALGORITHM_RESULT_SETS = [
    (
        f"v3 (Project Code 가중치 {weight:,})",
        {
            "daily": f"DailyPlacement_mixW{weight}_LNS2000_7805.csv",
            "assign": f"AssignResult_mixW{weight}_LNS2000_7805.csv",
            "summary": f"Summary_mixW{weight}_LNS2000_7805.csv",
            "mixing_weight": weight,
        },
    )
    for weight in V3_MIXING_WEIGHTS
]

YARD_DIAGRAM_WIDTH = 900
YARD_DIAGRAM_HEIGHT = 560
YARD_DIAGRAM_SCALE = 1.28

PLOTLY_LOCKED_CONFIG = {
    "displayModeBar": False,
    "responsive": False,
    "scrollZoom": False,
    "doubleClick": False,
}

CSS = """
<style>
[data-testid="stAppViewContainer"] > .main { background: #f1f5f9; }
[data-testid="stSidebar"] { background: #0f172a !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: #e2e8f0; }
.st-key-previous_day_button button,
.st-key-next_day_button button {
    padding: 0 !important;
    min-height: 2.5rem !important;
}
.st-key-previous_day_button button p,
.st-key-next_day_button button p {
    color: #f8fafc !important;
    font-size: 1.3rem !important;
    font-weight: 800 !important;
    line-height: 1 !important;
}
.section-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0 0 4px 0;
}
.yard-diagram-scroll { overflow-x: auto; padding-bottom: 8px; }
.stack-board {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 10px;
    align-items: start;
    margin-top: 12px;
}
.stack-focus {
    background: #ffffff;
    border: 1px solid #d7dee8;
    border-radius: 10px;
    padding: 16px;
    color: #0f172a;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
    margin-bottom: 14px;
}
.stack-focus-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    margin-bottom: 12px;
}
.stack-focus-title {
    font-size: 1.05rem;
    font-weight: 800;
    color: #0f172a;
}
.stack-focus-sub {
    margin-top: 3px;
    color: #64748b;
    font-size: 0.78rem;
}
.stack-focus-metrics {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
}
.stack-pill {
    background: #f1f5f9;
    border: 1px solid #dbe4ee;
    border-radius: 999px;
    padding: 5px 9px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #334155;
}
.stack-focus-grid {
    display: grid;
    gap: 7px;
    width: 100%;
}
.stack-slot-head, .stack-level-head {
    min-height: 34px;
    border-radius: 7px;
    background: #eef3f8;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
}
.stack-level-head.fourth-label {
    color: #b91c1c;
    background: #fff1f2;
}
.stack-focus-cell {
    min-height: 58px;
    border-radius: 8px;
    border: 1px solid #dbe4ee;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 6px;
    overflow: hidden;
}
.stack-focus-cell.filled {
    border-color: rgba(15, 23, 42, 0.16);
    color: #ffffff;
    box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.16);
}
.stack-focus-cell.fourth {
    box-shadow: inset 0 0 0 3px #ef4444;
}
.stack-cell-main {
    font-size: 0.76rem;
    font-weight: 800;
    line-height: 1.05;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stack-cell-sub {
    margin-top: 4px;
    font-size: 0.63rem;
    font-weight: 700;
    opacity: 0.86;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stack-card {
    background: #ffffff;
    border: 1px solid #d7dee8;
    border-radius: 8px;
    padding: 10px;
    color: #0f172a;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}
.stack-card-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 0.82rem;
    font-weight: 800;
    margin-bottom: 2px;
}
.stack-card-sub {
    color: #64748b;
    font-size: 0.68rem;
    margin-bottom: 8px;
}
.stack-mini-grid {
    display: grid;
    gap: 2px;
    width: 100%;
}
.stack-axis {
    min-height: 16px;
    color: #64748b;
    font-size: 0.58rem;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
}
.stack-cell {
    height: 15px;
    min-width: 12px;
    border-radius: 3px;
    border: 1px solid #dbe4ee;
    background: #f1f5f9;
}
.stack-cell.filled {
    border-color: rgba(15, 23, 42, 0.18);
}
.stack-cell.fourth {
    outline: 2px solid #dc2626;
    outline-offset: -2px;
}
.stack-empty-note {
    color: #64748b;
    font-size: 0.74rem;
    padding: 8px 0 4px 0;
}
</style>
"""


@st.cache_data(ttl=300)
def load_daily_placement(program_run_dir: str, daily_file: str = DAILY_PLACEMENT_FILE) -> pd.DataFrame:
    path = Path(program_run_dir) / daily_file
    if not path.exists():
        st.error(f"{daily_file} not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    for col in [
        "day", "yard_index", "slot_index_1based", "level_index_1based",
        "packing_index", "effective_height_mm", "cum_level_height",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["yard_name", "packing_id", "project_code", "project_name", "group_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "yard_name" in df.columns:
        df["yard_name"] = df["yard_name"].str.upper()
    return df


@st.cache_data(ttl=300)
def load_yard_config(program_run_dir: str) -> pd.DataFrame:
    path = Path(program_run_dir) / YARD_CONFIG_FILE
    if not path.exists():
        st.error(f"YardInputWithStack.csv not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df["yard_name"] = df["yard_name"].astype(str).str.strip().str.upper()
    if "sector" in df.columns:
        df["sector"] = df["sector"].astype(str).str.strip().str.upper()
    else:
        df["sector"] = df["yard_name"].str.extract(r"^([A-Z]+)", expand=False).fillna("")

    for col in [
        "capacity", "distance", "x", "y", "yard_index", "slot_count",
        "normal_level", "max_level", "allow_fourth_level", "max_stack_height_mm",
        "is_main_sector", "allow_mixed_project", "is_available_default",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["block"] = df["yard_name"].str[0]
    return df


@st.cache_data(ttl=300)
def load_assignment_result(program_run_dir: str, assign_file: str = ASSIGN_RESULT_FILE) -> pd.DataFrame:
    path = Path(program_run_dir) / assign_file
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    df["yard_name"] = df["yard_name"].astype(str).str.strip().str.upper()
    df["project_name"] = df["project_name"].astype(str).str.strip()
    df["project_code"] = df["project_name"].str.split("_").str[0]
    for col in ["number", "start_day", "end_day", "is_fixed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_objective_term_comparison(program_run_dir: str) -> pd.DataFrame:
    """Load field and selected project-code-weight objective terms."""
    term_keys = [
        "relocation_sum",
        "total_weighted_dist_sum",
        "total_project_dist_sum",
        "project_yard_num",
        "total_assigned_package_num",
    ]
    term_labels = {
        "relocation_sum": "재취급 대상 packing 수",
        "total_weighted_dist_sum": "지게차 이동거리",
        "total_project_dist_sum": "동일 프로젝트 분산거리",
        "project_yard_num": "Project-yard 배정 건수",
        "total_assigned_package_num": "배정 packing 수",
    }

    values_by_source: dict[str, dict[str, float]] = {}
    field_path = Path(program_run_dir) / FIELD_OBJECT_SUMMARY_FILE
    if field_path.exists():
        field_raw = pd.read_csv(field_path)
        if {"term", "value"}.issubset(field_raw.columns):
            field_values = pd.to_numeric(field_raw["value"], errors="coerce")
            values_by_source["현업"] = dict(zip(field_raw["term"].astype(str), field_values))

    for _, files in ALGORITHM_RESULT_SETS:
        summary_file = files.get("summary")
        if not summary_file:
            continue

        summary_path = Path(program_run_dir) / summary_file
        if not summary_path.exists():
            continue

        parsed: dict[str, float] = {}
        for raw_line in summary_path.read_text(encoding="utf-8-sig").splitlines():
            if ":" not in raw_line:
                continue
            key, raw_value = raw_line.split(":", 1)
            key = key.strip()
            if key not in term_keys:
                continue
            value = pd.to_numeric(raw_value.strip(), errors="coerce")
            if pd.notna(value):
                parsed[key] = float(value)

        mixing_weight = int(files["mixing_weight"])
        values_by_source[f"W{mixing_weight}"] = parsed

    source_labels = ["현업"] + [f"W{weight}" for weight in V3_MIXING_WEIGHTS]

    rows = []
    for key in term_keys:
        row = {"항목": term_labels[key], "term": key}
        for source in source_labels:
            row[source] = values_by_source.get(source, {}).get(key, pd.NA)
        rows.append(row)

    common_weights = {
        "relocation_sum": 200.0,
        "total_weighted_dist_sum": 1.0,
        "total_project_dist_sum": 1.0,
        "project_yard_num": 1.0,
    }
    objective_row = {
        "항목": "공통 목적값 (weight: 200, 1, 1, 1)",
        "term": "common_obj_value",
    }
    for source in source_labels:
        source_values = values_by_source.get(source, {})
        if all(key in source_values for key in common_weights):
            objective_row[source] = sum(
                source_values[key] * weight
                for key, weight in common_weights.items()
            )
        else:
            objective_row[source] = pd.NA
    rows.append(objective_row)

    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_v3_weight_comparison(program_run_dir: str) -> pd.DataFrame:
    """Load the v3 project-code-weight experiment summary."""
    path = Path(program_run_dir) / "MixingWeightExperimentSummary_LNS2000_7805.csv"
    if not path.exists():
        return pd.DataFrame()

    comparison = pd.read_csv(path)
    required_columns = {
        "mixing_weight",
        "relocation_sum",
        "total_weighted_dist_sum",
        "total_project_dist_sum",
        "project_yard_num",
        "total_assigned_package_num",
        "project_mixing_penalty",
        "mixed_yards",
        "mixed_yard_days",
        "max_project_codes_in_same_yard_day",
        "used_yards",
        "runtime_sec",
    }
    if not required_columns.issubset(comparison.columns):
        return pd.DataFrame()

    numeric_columns = list(required_columns)
    for column in numeric_columns:
        comparison[column] = pd.to_numeric(comparison[column], errors="coerce")

    comparison = comparison[
        comparison["mixing_weight"].isin(V3_MIXING_WEIGHTS)
    ].copy()

    comparison["common_obj_value"] = (
        comparison["relocation_sum"] * 200.0
        + comparison["total_weighted_dist_sum"]
        + comparison["total_project_dist_sum"]
        + comparison["project_yard_num"]
    )

    return comparison.sort_values("mixing_weight").reset_index(drop=True)


@st.cache_data(ttl=300)
def load_field_utilization(program_run_dir: str) -> pd.DataFrame:
    """Optional Jeil Technos baseline utilization file.

    Supported formats:
    1) yard_name, jeil_avg_utilization
       - values can be 0.56, 56, or "56%"
    2) yard_name, day, usage, capacity
       - average utilization is computed by yard.
    """
    path = Path(program_run_dir) / FIELD_UTILIZATION_FILE
    if not path.exists():
        return pd.DataFrame(columns=["yard_name", "jeil_avg_utilization"])

    raw = pd.read_csv(path)
    raw.columns = [str(col).strip() for col in raw.columns]
    lower_to_original = {col.lower(): col for col in raw.columns}

    if "yard_name" not in lower_to_original and "yard" in lower_to_original:
        raw = raw.rename(columns={lower_to_original["yard"]: "yard_name"})
    elif "yard_name" in lower_to_original:
        raw = raw.rename(columns={lower_to_original["yard_name"]: "yard_name"})

    if "yard_name" not in raw.columns:
        st.warning(f"{FIELD_UTILIZATION_FILE} needs a yard_name column.")
        return pd.DataFrame(columns=["yard_name", "jeil_avg_utilization"])

    raw["yard_name"] = raw["yard_name"].astype(str).str.strip().str.upper()

    util_candidates = [
        "jeil_avg_utilization",
        "jeil_avg_util",
        "field_avg_utilization",
        "field_avg_util",
        "avg_utilization",
        "utilization",
    ]
    lower_to_original = {col.lower(): col for col in raw.columns}
    util_col = next((lower_to_original[col] for col in util_candidates if col in lower_to_original), None)

    if util_col is not None:
        out = raw[["yard_name", util_col]].copy()
        out = out.rename(columns={util_col: "jeil_avg_utilization"})
        out["jeil_avg_utilization"] = normalize_utilization_series(out["jeil_avg_utilization"])
        return out.groupby("yard_name", as_index=False)["jeil_avg_utilization"].mean()

    usage_col = lower_to_original.get("usage") or lower_to_original.get("packing_count") or lower_to_original.get("count")
    capacity_col = lower_to_original.get("capacity") or lower_to_original.get("capa")
    if usage_col and capacity_col:
        temp = raw[["yard_name", usage_col, capacity_col]].copy()
        temp[usage_col] = pd.to_numeric(temp[usage_col], errors="coerce").fillna(0.0)
        temp[capacity_col] = pd.to_numeric(temp[capacity_col], errors="coerce").replace(0, pd.NA)
        temp["utilization"] = (temp[usage_col] / temp[capacity_col]).fillna(0.0)
        return temp.groupby("yard_name", as_index=False).agg(jeil_avg_utilization=("utilization", "mean"))

    st.warning(
        f"{FIELD_UTILIZATION_FILE} was found, but no utilization columns were recognized. "
        "Use yard_name, jeil_avg_utilization or yard_name, day, usage, capacity."
    )
    return pd.DataFrame(columns=["yard_name", "jeil_avg_utilization"])



@st.cache_data(ttl=300)
def load_jeil_project_yard_usage(program_run_dir: str) -> pd.DataFrame:
    """Optional Jeil Technos project-yard usage file.

    Expected file: Program_run/JeilProjectYardUsage.csv

    Supported columns:
    - project_code, yard_name, packing_count
    - project_code, yard_name, number
    - project_name, yard_name, number  (project_code is inferred before "_")
    """
    path = Path(program_run_dir) / JEIL_PROJECT_YARD_FILE
    if not path.exists():
        return pd.DataFrame(columns=["yard_name", "project_code", "project_name", "packing_count"])

    raw = pd.read_csv(path)
    raw.columns = [str(col).strip() for col in raw.columns]
    lower_to_original = {col.lower(): col for col in raw.columns}

    rename_map = {}
    if "yard" in lower_to_original and "yard_name" not in lower_to_original:
        rename_map[lower_to_original["yard"]] = "yard_name"
    if "yard_name" in lower_to_original:
        rename_map[lower_to_original["yard_name"]] = "yard_name"
    if "project_code" in lower_to_original:
        rename_map[lower_to_original["project_code"]] = "project_code"
    if "project_name" in lower_to_original:
        rename_map[lower_to_original["project_name"]] = "project_name"

    count_col = None
    for candidate in ["packing_count", "number", "assigned_num", "count", "packings"]:
        if candidate in lower_to_original:
            count_col = lower_to_original[candidate]
            break
    if count_col is not None:
        rename_map[count_col] = "packing_count"

    raw = raw.rename(columns=rename_map)

    required = {"yard_name", "packing_count"}
    if not required.issubset(set(raw.columns)) or not ({"project_code", "project_name"} & set(raw.columns)):
        st.warning(
            f"{JEIL_PROJECT_YARD_FILE} was found, but columns were not recognized. "
            "Use project_code,yard_name,packing_count."
        )
        return pd.DataFrame(columns=["yard_name", "project_code", "project_name", "packing_count"])

    raw["yard_name"] = raw["yard_name"].astype(str).str.strip().str.upper()
    if "project_code" not in raw.columns:
        raw["project_code"] = raw["project_name"].astype(str).str.split("_").str[0]
    if "project_name" not in raw.columns:
        raw["project_name"] = raw["project_code"].astype(str)

    raw["project_code"] = raw["project_code"].astype(str).str.strip()
    raw["project_name"] = raw["project_name"].astype(str).str.strip()
    raw["packing_count"] = pd.to_numeric(raw["packing_count"], errors="coerce").fillna(0.0)

    return (
        raw.groupby(["yard_name", "project_code", "project_name"], as_index=False)
        .agg(packing_count=("packing_count", "sum"))
    )
def day_to_date_label(day: int) -> str:
    base = datetime.strptime(BASE_DATE_STR, "%Y-%m-%d")
    return (base + timedelta(days=int(day) - 1)).strftime("%Y-%m-%d")


def yard_sort_key(yard_name: str) -> tuple:
    text = str(yard_name).strip().upper()
    prefix = "".join(ch for ch in text if ch.isalpha())
    suffix = "".join(ch for ch in text if ch.isdigit())
    return prefix, int(suffix) if suffix else 0, text


PROJECT_COLOR_PALETTE = (
    px.colors.qualitative.Bold
    + px.colors.qualitative.Plotly
    + px.colors.qualitative.Dark24
    + px.colors.qualitative.Light24
    + px.colors.qualitative.Alphabet
)


def get_project_color(project_name: str) -> str:
    hash_hex = hashlib.md5(str(project_name).encode("utf-8")).hexdigest()
    color_index = int(hash_hex[:8], 16) % len(PROJECT_COLOR_PALETTE)
    return PROJECT_COLOR_PALETTE[color_index]


def build_discrete_color_map(values: pd.Series | list) -> dict[str, str]:
    """Assign clearly separated colors to visible project/group keys."""
    keys = sorted({
        str(value).strip()
        for value in values
        if str(value).strip() not in ("", "nan", "None")
    })
    return {
        key: PROJECT_COLOR_PALETTE[index % len(PROJECT_COLOR_PALETTE)]
        for index, key in enumerate(keys)
    }


def build_yard_day(daily_df: pd.DataFrame, yards_df: pd.DataFrame, selected_day: int) -> pd.DataFrame:
    day_df = daily_df[daily_df["day"] == selected_day].copy()
    usage = (
        day_df.groupby("yard_name")
        .agg(usage=("packing_id", "count"), project_count=("project_code", "nunique"))
        .reset_index()
        if not day_df.empty else pd.DataFrame(columns=["yard_name", "usage", "project_count"])
    )

    yard_day = yards_df.merge(usage, on="yard_name", how="left")
    yard_day["usage"] = yard_day["usage"].fillna(0.0)
    yard_day["project_count"] = yard_day["project_count"].fillna(0.0)
    yard_day["capacity"] = yard_day["capacity"].fillna(0.0)
    yard_day["distance"] = yard_day.get("distance", 0).fillna(0.0)
    yard_day["utilization"] = yard_day.apply(
        lambda row: float(row["usage"]) / float(row["capacity"]) if float(row["capacity"] or 0) > 0 else 0.0,
        axis=1,
    )
    yard_day["over_capacity"] = yard_day["usage"] > yard_day["capacity"]
    return yard_day


def build_diagram_boxes(yard_day: pd.DataFrame) -> pd.DataFrame:
    """Build the hand-drawn yard diagram used for discussion slides.

    J yards are intentionally hidden because they are not part of the current
    operating view. The diagram keeps the previous visual layout, but it now
    includes the current yard counts: F/D/B up to 17, A/C/E/G up to 10, and H up
    to 19. Values still come from YardInputWithStack.csv and the result files.
    """
    records = []

    def add_box(yard_name: str, x0: float, y0: float, x1: float, y1: float) -> None:
        yard_name = yard_name.upper()
        match = yard_day[yard_day["yard_name"] == yard_name]
        if match.empty:
            return
        row = match.iloc[0].to_dict()
        row.update({
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2,
        })
        records.append(row)

    def existing_nums(prefix: str) -> list[int]:
        names = yard_day["yard_name"].astype(str).str.upper()
        nums = []
        for name in names[names.str.startswith(prefix)]:
            suffix = name[len(prefix):]
            if suffix.isdigit():
                nums.append(int(suffix))
        return sorted(nums)

    def add_vertical_stack(prefix: str, nums: list[int], x0: float, y0: float, x1: float, y1: float) -> None:
        if not nums:
            return
        gap = 2.0
        height = (y1 - y0) / len(nums)
        for idx, num in enumerate(nums):
            add_box(f"{prefix}{num:02d}", x0, y0 + idx * height + gap / 2, x1, y0 + (idx + 1) * height - gap / 2)

    def add_horizontal_stack(prefix: str, nums: list[int], x0: float, y0: float, x1: float, y1: float) -> None:
        if not nums:
            return
        gap = 2.0
        width = (x1 - x0) / len(nums)
        for idx, num in enumerate(nums):
            add_box(f"{prefix}{num:02d}", x0 + idx * width + gap / 2, y0, x0 + (idx + 1) * width - gap / 2, y1)

    # Main left blocks. These preserve the older yard-map composition.
    add_vertical_stack("F", sorted(existing_nums("F"), reverse=True), 17, 5, 96, 340)
    add_vertical_stack("D", sorted(existing_nums("D"), reverse=True), 104, 5, 184, 340)
    add_vertical_stack("B", sorted(existing_nums("B"), reverse=True), 225, 5, 306, 340)

    # Lower blocks. Draw all current 01-10 yards instead of the old 01-08 subset.
    add_vertical_stack("E", sorted(existing_nums("E"), reverse=True), 17, 360, 96, 552)
    add_vertical_stack("C", sorted(existing_nums("C"), reverse=True), 104, 360, 184, 552)
    add_vertical_stack("A", sorted(existing_nums("A"), reverse=True), 220, 360, 305, 552)

    g_nums = existing_nums("G")
    add_vertical_stack("G", sorted([n for n in g_nums if n <= 8], reverse=True), 318, 360, 397, 552)
    add_box("G10", 318, 55, 397, 78)
    add_box("G09", 318, 84, 397, 107)

    # H is laid out in two horizontal rows around the factory area.
    h_nums = existing_nums("H")
    add_horizontal_stack("H", [n for n in range(8, 22) if n in h_nums], 465, 110, 762, 170)
    add_horizontal_stack("H", [n for n in range(1, 8) if n in h_nums], 465, 182, 615, 242)

    # J yards are deliberately not drawn in this operating view.
    return pd.DataFrame(records)

def add_factory_areas(fig: go.Figure) -> None:
    factory_fill = "rgba(251, 146, 60, 0.22)"
    factory_line = dict(color="rgba(234, 88, 12, 0.55)", width=1.4)
    fig.add_shape(
        type="path",
        path="M 490 18 L 840 18 L 840 510 L 465 510 L 465 250 L 620 250 L 620 180 L 785 180 L 785 94 L 490 94 Z",
        fillcolor=factory_fill,
        line=factory_line,
        layer="below",
    )
    for x, y in [(665, 56), (645, 370)]:
        fig.add_annotation(
            x=x,
            y=y,
            text="Factory",
            showarrow=False,
            font=dict(size=14, color="rgba(154, 52, 18, 0.75)"),
            textangle=-12,
        )


def render_yard_diagram(
    yard_day: pd.DataFrame,
    selected_yard: str,
    highlight_values: dict[str, float] | None = None,
    highlight_label: str = "Project packings",
    highlight_heatmap: bool = False,
    annotation_values: dict[str, float] | None = None,
    annotation_label: str = "Value",
    chart_key: str = "yard_diagram_chart",
    show_metric_numbers: bool = True,
) -> None:
    boxes = build_diagram_boxes(yard_day)
    fig = go.Figure()
    add_factory_areas(fig)

    highlight_values = highlight_values or {}
    annotation_values = annotation_values or {}
    selected_yard = str(selected_yard).strip().upper()
    positive = [float(v) for v in highlight_values.values() if float(v) > 0]
    max_highlight = max(positive) if positive else 0.0

    for _, row in boxes.iterrows():
        yard_name = row["yard_name"]
        is_selected = yard_name == selected_yard
        highlight_value = float(highlight_values.get(yard_name, 0))
        is_highlighted = highlight_value > 0

        if is_highlighted and highlight_heatmap and max_highlight > 0:
            ratio = highlight_value / max_highlight
            if ratio >= 0.75:
                fillcolor = "rgba(21, 128, 61, 0.88)"
            elif ratio >= 0.5:
                fillcolor = "rgba(22, 163, 74, 0.76)"
            elif ratio >= 0.25:
                fillcolor = "rgba(74, 222, 128, 0.64)"
            else:
                fillcolor = "rgba(187, 247, 208, 0.62)"
        elif is_highlighted:
            fillcolor = "rgba(34, 197, 94, 0.42)"
        else:
            fillcolor = "rgba(226, 232, 240, 0.55)" if highlight_values else "rgba(219, 234, 254, 0.5)"

        # In project/highlight maps, unused yards should recede into a neutral gray.
        # This keeps attention on the green highlighted yards instead of blue outlines.
        if is_selected:
            line_color = "#dc2626"
        elif is_highlighted:
            line_color = "#16a34a"
        elif highlight_values:
            line_color = "#94a3b8"
        else:
            line_color = "#1d4ed8"
        line_width = 3 if is_selected else (2.4 if is_highlighted else 1.4)
        fig.add_shape(
            type="rect",
            x0=row["x0"], y0=row["y0"], x1=row["x1"], y1=row["y1"],
            fillcolor=fillcolor,
            line=dict(color=line_color, width=line_width),
            layer="above",
        )

    hover_text = []
    for _, row in boxes.iterrows():
        name = row["yard_name"]
        lines = [
            f"<b>{name}</b>",
            f"Capacity: {float(row.get('capacity', 0)):,.0f}",
            f"Usage: {float(row.get('usage', 0)):,.0f}",
            f"Utilization: {float(row.get('utilization', 0)):.1%}",
            f"Project count: {float(row.get('project_count', 0)):,.0f}",
        ]
        if highlight_values:
            lines.insert(1, f"{highlight_label}: {float(highlight_values.get(name, 0)):,.0f}")
        if annotation_values:
            lines.insert(1, f"{annotation_label}: {float(annotation_values.get(name, 0)):,.0f}")
        hover_text.append("<br>".join(lines))

    label_text = []
    for _, row in boxes.iterrows():
        name = row["yard_name"]
        annotation_value = float(annotation_values.get(name, 0))
        highlight_value = float(highlight_values.get(name, 0))
        # Project-yard maps are easier to read with color only; keep counts in hover text.
        if show_metric_numbers and annotation_value > 0:
            label_text.append(f"<b>{name}</b><br><span style='color:#c2410c'><b>{annotation_value:,.0f}</b></span>")
        elif show_metric_numbers and highlight_value > 0:
            label_text.append(f"<b>{name}</b><br><span style='color:#166534'><b>{highlight_value:,.0f}</b></span>")
        else:
            label_text.append(f"<b>{name}</b>")

    fig.add_trace(go.Scatter(
        x=boxes["cx"],
        y=boxes["cy"],
        mode="markers+text",
        text=label_text,
        textposition="middle center",
        textfont=dict(size=10, color="#0f172a"),
        marker=dict(size=24, color="rgba(255,255,255,0.01)"),
        customdata=boxes["yard_name"].tolist(),
        hovertext=hover_text,
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        width=int(YARD_DIAGRAM_WIDTH * YARD_DIAGRAM_SCALE),
        height=int(YARD_DIAGRAM_HEIGHT * YARD_DIAGRAM_SCALE),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
    )
    fig.update_xaxes(visible=False, range=[0, YARD_DIAGRAM_WIDTH], constrain="domain", fixedrange=True)
    fig.update_yaxes(visible=False, range=[YARD_DIAGRAM_HEIGHT, 0], scaleanchor="x", scaleratio=1, fixedrange=True)

    st.markdown('<div class="yard-diagram-scroll">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=False, config=PLOTLY_LOCKED_CONFIG, key=chart_key)
    st.markdown("</div>", unsafe_allow_html=True)


def build_project_yard_usage(daily_df: pd.DataFrame, assign_df: pd.DataFrame, mode: str, selected_day: int) -> pd.DataFrame:
    if mode == "Daily active" or assign_df.empty:
        base = daily_df[daily_df["day"] == selected_day].copy()
        if base.empty:
            return pd.DataFrame(columns=["yard_name", "project_code", "project_name", "packing_count"])
        return (
            base.groupby(["yard_name", "project_code", "project_name"])
            .agg(packing_count=("packing_id", "count"))
            .reset_index()
        )

    return (
        assign_df.groupby(["yard_name", "project_code", "project_name"])
        .agg(packing_count=("number", "sum"))
        .reset_index()
    )


def build_project_stats(usage_df: pd.DataFrame) -> pd.DataFrame:
    if usage_df.empty:
        return pd.DataFrame(columns=["project_code", "yard_count", "total_number"])
    return (
        usage_df.groupby("project_code")
        .agg(yard_count=("yard_name", "nunique"), total_number=("packing_count", "sum"))
        .reset_index()
        .sort_values(["yard_count", "total_number", "project_code"], ascending=[False, False, True])
    )


def get_packings_for_yard_day(daily_df: pd.DataFrame, yard_name: str, day: int) -> pd.DataFrame:
    active = daily_df[(daily_df["yard_name"] == yard_name) & (daily_df["day"] == day)].copy()
    if active.empty:
        return active
    return active.sort_values(["slot_index_1based", "level_index_1based", "packing_index"])


def render_slot_grid(active: pd.DataFrame, config_row: pd.Series) -> None:
    slot_count = int(config_row.get("slot_count", 0) or 0)
    normal_level = int(config_row.get("normal_level", 3) or 3)
    max_level = int(config_row.get("max_level", normal_level) or normal_level)
    if slot_count <= 0:
        st.info("slot_count is not available.")
        return

    fig = go.Figure()
    color_map = build_discrete_color_map(
        active["project_code"] if "project_code" in active.columns else []
    )
    for slot in range(1, slot_count + 1):
        for level in range(1, max_level + 1):
            fig.add_shape(
                type="rect",
                x0=slot - 0.45, x1=slot + 0.45,
                y0=level - 0.42, y1=level + 0.42,
                fillcolor="rgba(230,230,230,0.45)",
                line=dict(color="rgba(120,120,120,0.45)", width=1),
                layer="below",
            )

    for _, row in active.iterrows():
        slot = int(row["slot_index_1based"])
        level = int(row["level_index_1based"])
        project_code = str(row.get("project_code", ""))
        project_name = str(row.get("project_name", project_code))
        color_key = project_code if project_code else project_name
        label = str(row.get("packing_id", row.get("packing_index", "")))
        border = "crimson" if level > normal_level else "white"
        fig.add_shape(
            type="rect",
            x0=slot - 0.45, x1=slot + 0.45,
            y0=level - 0.42, y1=level + 0.42,
            fillcolor=color_map.get(color_key, get_project_color(color_key)),
            line=dict(color=border, width=2),
            layer="below",
        )
        fig.add_trace(go.Scatter(
            x=[slot], y=[level], mode="text", text=[label],
            textfont=dict(size=10, color="white"),
            hovertemplate=(
                f"<b>packing:</b> {label}<br>"
                f"<b>project_code:</b> {project_code}<br>"
                f"<b>project:</b> {project_name}<br>"
                f"<b>slot:</b> {slot}<br>"
                f"<b>level:</b> {level}<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text="slot / level grid", font=dict(color="#111827", size=16)),
        xaxis=dict(
            title=dict(text="slot", font=dict(color="#111827", size=13)),
            tickmode="array",
            tickvals=list(range(1, slot_count + 1)),
            tickfont=dict(color="#111827", size=12),
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.22)",
            gridwidth=1,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="level", font=dict(color="#111827", size=13)),
            tickmode="array",
            tickvals=list(range(1, max_level + 1)),
            tickfont=dict(color="#111827", size=12),
            range=[0.5, max_level + 0.5],
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.22)",
            gridwidth=1,
            zeroline=False,
        ),
        height=380,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#111827"),
        margin=dict(l=60, r=20, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)



def render_daily_stacking_board(
    daily_df: pd.DataFrame,
    yards_df: pd.DataFrame,
    selected_day: int,
    selected_blocks: list[str],
    focus_yard: str,
    show_empty_yards: bool,
    show_overview_cards: bool,
    max_yard_cards: int,
    color_by: str,
) -> None:
    """Render a focused day/yard slot-level board plus optional yard overview cards.

    The first board is intentionally large and readable: one selected yard, slot
    columns, level rows. The small cards below are only an overview for scanning
    which yards are active on the same day.
    """
    day_df = daily_df[daily_df["day"] == selected_day].copy()
    if day_df.empty:
        st.info("No active packing on selected day.")
        return

    yard_configs = yards_df.copy()
    if selected_blocks:
        yard_configs = yard_configs[yard_configs["block"].isin(selected_blocks)]

    usage = (
        day_df.groupby("yard_name")
        .agg(
            packing_count=("packing_id", "count"),
            project_count=("project_code", "nunique"),
            fourth_count=("level_index_1based", lambda s: int((pd.to_numeric(s, errors="coerce") >= 4).sum())),
        )
        .reset_index()
    )

    yard_configs = yard_configs.merge(usage, on="yard_name", how="left")
    for col in ["packing_count", "project_count", "fourth_count"]:
        yard_configs[col] = yard_configs[col].fillna(0).astype(int)

    if yard_configs.empty:
        st.info("No yards match the selected block filters.")
        return

    yard_configs = yard_configs.sort_values("yard_name", key=lambda s: s.map(yard_sort_key))
    if focus_yard not in set(yard_configs["yard_name"].astype(str)):
        active_candidates = yard_configs[yard_configs["packing_count"] > 0]
        if not active_candidates.empty:
            focus_yard = str(active_candidates.iloc[0]["yard_name"])
        else:
            focus_yard = str(yard_configs.iloc[0]["yard_name"])

    focus_cfg = yard_configs[yard_configs["yard_name"].astype(str) == str(focus_yard)].iloc[0]
    focus_active = get_packings_for_yard_day(day_df, str(focus_yard), selected_day)

    slot_count = int(focus_cfg.get("slot_count", 0) or 0)
    normal_level = int(focus_cfg.get("normal_level", 3) or 3)
    max_level = int(focus_cfg.get("max_level", normal_level) or normal_level)
    capacity = int(focus_cfg.get("capacity", 0) or 0)
    color_column = color_by if color_by in day_df.columns else "project_code"
    occupied: dict[tuple[int, int], pd.Series] = {}
    for _, row in focus_active.iterrows():
        try:
            slot = int(row["slot_index_1based"])
            level = int(row["level_index_1based"])
        except Exception:
            continue
        occupied[(slot, level)] = row

    active_count = int(len(focus_active))
    project_count = int(focus_active["project_code"].nunique()) if "project_code" in focus_active.columns else 0
    fourth_count = int((pd.to_numeric(focus_active.get("level_index_1based", pd.Series(dtype=float)), errors="coerce") >= 4).sum())

    focus_parts: list[str] = []
    focus_parts.append("<div class='stack-focus'>")
    focus_parts.append("<div class='stack-focus-head'>")
    focus_parts.append(
        f"<div><div class='stack-focus-title'>{html.escape(str(focus_yard))} | "
        f"day {selected_day} ({day_to_date_label(selected_day)})</div>"
        f"<div class='stack-focus-sub'>slot columns / level rows / color by {html.escape(color_column)}</div></div>"
    )
    focus_parts.append("<div class='stack-focus-metrics'>")
    focus_parts.append(f"<span class='stack-pill'>packings {active_count}</span>")
    focus_parts.append(f"<span class='stack-pill'>projects {project_count}</span>")
    focus_parts.append(f"<span class='stack-pill'>capacity {capacity}</span>")
    focus_parts.append(f"<span class='stack-pill'>4th {fourth_count}</span>")
    focus_parts.append("</div></div>")

    grid_style = f"grid-template-columns: 58px repeat({max(slot_count, 1)}, minmax(68px, 1fr));"
    focus_parts.append(f"<div class='stack-focus-grid' style='{grid_style}'>")
    focus_parts.append("<div class='stack-slot-head'></div>")
    for slot in range(1, slot_count + 1):
        focus_parts.append(f"<div class='stack-slot-head'>{slot}</div>")

    for level in range(max_level, 0, -1):
        label_class = "stack-level-head fourth-label" if level > normal_level else "stack-level-head"
        level_label = f"{level}"
        focus_parts.append(f"<div class='{label_class}'>{level_label}</div>")
        for slot in range(1, slot_count + 1):
            row = occupied.get((slot, level))
            if row is None:
                focus_parts.append("<div class='stack-focus-cell' title='empty'></div>")
                continue

            color_key = str(row.get(color_column, row.get("project_code", "")))
            # Keep the same project/group color across every day.
            color = get_project_color(color_key)
            packing_id = str(row.get("packing_id", ""))
            project_code = str(row.get("project_code", ""))
            group_id = str(row.get("group_id", ""))
            height = str(row.get("effective_height_mm", ""))
            packing_short = packing_id.rsplit("_", 1)[-1] if "_" in packing_id else packing_id[-4:]
            main_text = html.escape(project_code)
            sub_text = html.escape(f"#{packing_short} / {height}mm")
            title = html.escape(
                f"yard={focus_yard}\nslot={slot}\nlevel={level}\npacking={packing_id}\nproject={project_code}\ngroup={group_id}\nheight={height}mm"
            )
            cls = "stack-focus-cell filled fourth" if level > normal_level else "stack-focus-cell filled"
            focus_parts.append(
                f"<div class='{cls}' style='background:{color};' title='{title}'>"
                f"<div class='stack-cell-main'>{main_text}</div>"
                f"<div class='stack-cell-sub'>{sub_text}</div>"
                "</div>"
            )
    focus_parts.append("</div></div>")
    st.markdown("".join(focus_parts), unsafe_allow_html=True)

    if not show_overview_cards:
        return

    overview_configs = yard_configs.copy()
    if not show_empty_yards:
        overview_configs = overview_configs[overview_configs["packing_count"] > 0]
    if max_yard_cards > 0:
        overview_configs = overview_configs.head(max_yard_cards)

    if overview_configs.empty:
        st.info("No overview yards match the selected filters.")
        return

    cards: list[str] = []
    for _, cfg in overview_configs.iterrows():
        yard_name = str(cfg["yard_name"])
        slot_count = int(cfg.get("slot_count", 0) or 0)
        normal_level = int(cfg.get("normal_level", 3) or 3)
        max_level = int(cfg.get("max_level", normal_level) or normal_level)
        active = get_packings_for_yard_day(day_df, yard_name, selected_day)

        occupied_small: dict[tuple[int, int], pd.Series] = {}
        for _, row in active.iterrows():
            try:
                slot = int(row["slot_index_1based"])
                level = int(row["level_index_1based"])
            except Exception:
                continue
            occupied_small[(slot, level)] = row

        grid_style = f"grid-template-columns: 24px repeat({max(slot_count, 1)}, minmax(12px, 1fr));"
        cells = [f"<div class='stack-mini-grid' style='{grid_style}'>"]
        cells.append("<div class='stack-axis'></div>")
        for slot in range(1, slot_count + 1):
            cells.append(f"<div class='stack-axis'>{slot}</div>")

        for level in range(max_level, 0, -1):
            level_label = f"{level}" if level <= normal_level else f"{level}*"
            cells.append(f"<div class='stack-axis'>{level_label}</div>")
            for slot in range(1, slot_count + 1):
                row = occupied_small.get((slot, level))
                if row is None:
                    cells.append("<div class='stack-cell' title='empty'></div>")
                    continue
                color_key = str(row.get(color_column, row.get("project_code", "")))
                color = get_project_color(color_key)
                title = html.escape(
                    f"yard={yard_name}\nslot={slot}\nlevel={level}\npacking={row.get('packing_id', '')}\nproject={row.get('project_code', '')}"
                )
                cls = "stack-cell filled fourth" if level > normal_level else "stack-cell filled"
                cells.append(f"<div class='{cls}' style='background:{color};' title='{title}'></div>")
        cells.append("</div>")

        grid_html = "<div class='stack-empty-note'>empty on selected day</div>" if active.empty else "".join(cells)
        selected_style = " style='border-color:#ef4444; box-shadow:0 0 0 2px rgba(239,68,68,0.18);'" if yard_name == focus_yard else ""
        cards.append(
            "".join([
                f"<div class='stack-card'{selected_style}>",
                "<div class='stack-card-head'>",
                f"<span>{html.escape(yard_name)}</span>",
                f"<span>{int(cfg['packing_count'])} / {int(cfg.get('capacity', 0) or 0)}</span>",
                "</div>",
                "<div class='stack-card-sub'>",
                f"projects {int(cfg['project_count'])} | slots {slot_count} | 4th {int(cfg['fourth_count'])}",
                "</div>",
                grid_html,
                "</div>",
            ])
        )

    st.markdown("<div class='stack-board'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
def render_yard_overview(daily_df: pd.DataFrame, selected_day: int, selected_yard: str) -> None:
    day_df = daily_df[daily_df["day"] == selected_day]
    if day_df.empty:
        st.info("No active packing on selected day.")
        return

    yard_stats = (
        day_df.groupby("yard_name")
        .agg(packing_count=("packing_id", "count"), project_count=("project_code", "nunique"))
        .reset_index()
        .sort_values("packing_count", ascending=True)
    )
    colors = ["#EF553B" if y == selected_yard else "#636EFA" for y in yard_stats["yard_name"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yard_stats["packing_count"],
        y=yard_stats["yard_name"],
        orientation="h",
        marker_color=colors,
        text=yard_stats["packing_count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Packing count: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title="Yard active packing count",
        xaxis_title="packing count",
        yaxis_title="yard",
        height=max(420, len(yard_stats) * 24),
        margin=dict(l=80, r=20, t=50, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_project_yard_map(yards_df: pd.DataFrame, yard_day: pd.DataFrame, usage_df: pd.DataFrame, selected_project: str, selected_yard: str, heatmap: bool, chart_key: str = "project_yard_diagram_chart", source_label: str = "") -> None:
    selected_usage = usage_df[
        (usage_df["project_code"].astype(str) == selected_project) |
        (usage_df["project_name"].astype(str) == selected_project)
    ].copy()

    if selected_usage.empty:
        st.info("No assignments match the selected project.")
        # Project usage view에서는 선택 yard를 빨간 테두리로 강조하지 않는다.
        # 이 화면의 핵심은 특정 project가 사용한 yard 분포이므로,
        # 빨간 선택 테두리가 초록 분포 강조를 방해하지 않도록 빈 값으로 넘긴다.
        render_yard_diagram(yard_day, "", chart_key=chart_key + "_empty")
        return

    yard_summary = (
        selected_usage.groupby("yard_name")
        .agg(number=("packing_count", "sum"))
        .reset_index()
        .sort_values("number", ascending=False)
    )
    highlight_values = dict(zip(yard_summary["yard_name"], yard_summary["number"]))
    total_number = float(yard_summary["number"].sum())
    used_yard_count = int(yard_summary["yard_name"].nunique())

    project_yard_day = yard_day.copy()
    project_yard_day["usage"] = project_yard_day["yard_name"].map(highlight_values).fillna(0.0)
    project_yard_day["utilization"] = 0.0
    project_yard_day["over_capacity"] = False

    st.markdown(
        f"Project `{selected_project}` uses **{used_yard_count} yards** "
        f"with **{total_number:,.0f} packings**."
    )
    render_yard_diagram(
        project_yard_day,
        "",
        highlight_values=highlight_values,
        highlight_label="Project packings",
        highlight_heatmap=heatmap,
        chart_key=chart_key,
        show_metric_numbers=False,
    )

    left, right = st.columns([1, 1])
    with left:
        st.markdown('<p class="section-title">Yard Packings</p>', unsafe_allow_html=True)
        st.dataframe(yard_summary.rename(columns={"yard_name": "yard", "number": "packing_count"}), use_container_width=True, hide_index=True, height=360)
    with right:
        selected_yard_data = selected_usage[selected_usage["yard_name"] == selected_yard].copy()
        st.markdown(f'<p class="section-title">Selected Yard Detail - {selected_yard}</p>', unsafe_allow_html=True)
        if selected_yard_data.empty:
            st.info(f"Project `{selected_project}` has no assignments in `{selected_yard}`.")
        else:
            st.dataframe(selected_yard_data.sort_values("packing_count", ascending=False), use_container_width=True, hide_index=True, height=360)


def render_project_yard_heatmap(usage_df: pd.DataFrame) -> None:
    if usage_df.empty:
        st.info("No usage data for heatmap.")
        return
    pivot = usage_df.pivot_table(
        index="project_code",
        columns="yard_name",
        values="packing_count",
        aggfunc="sum",
        fill_value=0,
    )
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    if len(pivot) > 80:
        pivot = pivot.head(80)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(x="yard", y="project", color="packing"),
    )
    fig.update_layout(height=max(420, min(1200, len(pivot) * 18 + 140)))
    st.plotly_chart(fig, use_container_width=True)



def normalize_utilization_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace("%", "", regex=False)
    values = pd.to_numeric(text, errors="coerce").fillna(0.0)
    if values.max() > 1.5:
        values = values / 100.0
    return values.clip(lower=0.0)


def build_algorithm_avg_utilization(daily_df: pd.DataFrame, yards_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df.empty or yards_df.empty:
        return pd.DataFrame(columns=["yard_name", "algorithm_avg_utilization"])

    min_day = int(daily_df["day"].min())
    max_day = int(daily_df["day"].max())
    day_index = pd.DataFrame({"day": list(range(min_day, max_day + 1))})
    yard_base = yards_df[["yard_name", "capacity", "block"]].copy()
    yard_base["capacity"] = pd.to_numeric(yard_base["capacity"], errors="coerce").fillna(0.0)

    grid = yard_base.merge(day_index, how="cross")
    usage = (
        daily_df.groupby(["yard_name", "day"])
        .agg(usage=("packing_id", "count"))
        .reset_index()
    )
    grid = grid.merge(usage, on=["yard_name", "day"], how="left")
    grid["usage"] = grid["usage"].fillna(0.0)
    grid["utilization"] = grid.apply(
        lambda row: float(row["usage"]) / float(row["capacity"]) if float(row["capacity"] or 0) > 0 else 0.0,
        axis=1,
    )

    return (
        grid.groupby(["yard_name", "block"], as_index=False)
        .agg(algorithm_avg_utilization=("utilization", "mean"))
    )


def build_utilization_comparison(daily_df: pd.DataFrame, yards_df: pd.DataFrame, field_df: pd.DataFrame) -> pd.DataFrame:
    algo = build_algorithm_avg_utilization(daily_df, yards_df)
    comparison = yards_df[["yard_name", "block", "capacity"]].copy()
    comparison = comparison.merge(algo[["yard_name", "algorithm_avg_utilization"]], on="yard_name", how="left")
    comparison["algorithm_avg_utilization"] = comparison["algorithm_avg_utilization"].fillna(0.0)

    if not field_df.empty:
        comparison = comparison.merge(field_df, on="yard_name", how="left")
    else:
        comparison["jeil_avg_utilization"] = pd.NA

    return comparison


def render_utilization_comparison_map(
    yards_df: pd.DataFrame,
    comparison: pd.DataFrame,
    selected_yard: str,
    algorithm_label: str,
) -> None:
    yard_day = yards_df.copy()
    yard_day["usage"] = 0.0
    yard_day["utilization"] = 0.0
    yard_day["over_capacity"] = False
    boxes = build_diagram_boxes(yard_day)
    comparison_by_yard = comparison.set_index("yard_name").to_dict("index") if not comparison.empty else {}

    diffs = []
    for yard_name, row in comparison_by_yard.items():
        jeil = row.get("jeil_avg_utilization")
        algo = row.get("algorithm_avg_utilization", 0.0)
        if pd.notna(jeil):
            diffs.append(float(algo) - float(jeil))
    max_abs_diff = max((abs(v) for v in diffs), default=0.0)

    fig = go.Figure()
    add_factory_areas(fig)

    hover_text = []
    for _, row in boxes.iterrows():
        yard_name = row["yard_name"]
        values = comparison_by_yard.get(yard_name, {})
        algo = float(values.get("algorithm_avg_utilization", 0.0) or 0.0)
        jeil_raw = values.get("jeil_avg_utilization", pd.NA)
        has_jeil = pd.notna(jeil_raw)
        jeil = float(jeil_raw) if has_jeil else 0.0
        diff = algo - jeil if has_jeil else 0.0

        if has_jeil and max_abs_diff > 0:
            ratio = abs(diff) / max_abs_diff
            alpha = 0.18 + 0.68 * ratio
            if diff > 0:
                fillcolor = f"rgba(37, 99, 235, {alpha:.2f})"
                line_color = "#1d4ed8"
            elif diff < 0:
                fillcolor = f"rgba(22, 163, 74, {alpha:.2f})"
                line_color = "#16a34a"
            else:
                fillcolor = "rgba(226, 232, 240, 0.55)"
                line_color = "#94a3b8"
        else:
            fillcolor = "rgba(226, 232, 240, 0.55)"
            line_color = "#94a3b8"

        is_selected = yard_name == selected_yard
        fig.add_shape(
            type="rect",
            x0=row["x0"], y0=row["y0"], x1=row["x1"], y1=row["y1"],
            fillcolor=fillcolor,
            line=dict(color="#dc2626" if is_selected else line_color, width=3 if is_selected else 1.5),
            layer="above",
        )

        if has_jeil:
            hover_text.append(
                "<br>".join([
                    f"<b>{yard_name}</b>",
                    f"Jeil avg utilization: {jeil:.1%}",
                    f"{algorithm_label} avg utilization: {algo:.1%}",
                    f"{algorithm_label} - Jeil: {diff:+.1%}",
                ])
            )
        else:
            hover_text.append(
                "<br>".join([
                    f"<b>{yard_name}</b>",
                    "Jeil avg utilization: not loaded",
                    f"{algorithm_label} avg utilization: {algo:.1%}",
                ])
            )

    fig.add_trace(go.Scatter(
        x=boxes["cx"], y=boxes["cy"],
        mode="markers+text",
        text=["<b>" + name + "</b>" for name in boxes["yard_name"]],
        textposition="middle center",
        textfont=dict(size=10, color="#0f172a"),
        marker=dict(size=24, color="rgba(255,255,255,0.01)"),
        customdata=boxes["yard_name"].tolist(),
        hovertext=hover_text,
        hoverinfo="text",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=12, color="rgba(37, 99, 235, 0.72)"), name=f"{algorithm_label} higher"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=12, color="rgba(22, 163, 74, 0.72)"), name="Jeil Technos higher"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=12, color="rgba(226, 232, 240, 0.75)"), name="No Jeil data"))

    fig.update_layout(
        width=int(YARD_DIAGRAM_WIDTH * YARD_DIAGRAM_SCALE),
        height=int(YARD_DIAGRAM_HEIGHT * YARD_DIAGRAM_SCALE),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(color="#0f172a")),
    )
    fig.update_xaxes(visible=False, range=[0, YARD_DIAGRAM_WIDTH], constrain="domain", fixedrange=True)
    fig.update_yaxes(visible=False, range=[YARD_DIAGRAM_HEIGHT, 0], scaleanchor="x", scaleratio=1, fixedrange=True)

    st.markdown('<div class="yard-diagram-scroll">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=False, config=PLOTLY_LOCKED_CONFIG, key="utilization_comparison_map")
    st.markdown("</div>", unsafe_allow_html=True)


def render_utilization_comparison_table(comparison: pd.DataFrame, algorithm_label: str) -> None:
    if comparison.empty:
        st.info("No utilization comparison data.")
        return

    block_summary = (
        comparison.groupby("block", as_index=False)
        .agg(
            jeil_avg_utilization=("jeil_avg_utilization", "mean"),
            algorithm_avg_utilization=("algorithm_avg_utilization", "mean"),
        )
        .sort_values("block")
    )
    block_summary["diff_algorithm_minus_jeil"] = block_summary["algorithm_avg_utilization"] - block_summary["jeil_avg_utilization"]

    display = block_summary.copy()
    for col in ["jeil_avg_utilization", "algorithm_avg_utilization", "diff_algorithm_minus_jeil"]:
        display[col] = display[col].map(lambda value: "-" if pd.isna(value) else f"{value:.1%}")

    display = display.rename(columns={
        "block": "block",
        "jeil_avg_utilization": "Jeil avg utilization",
        "algorithm_avg_utilization": f"{algorithm_label} avg utilization",
        "diff_algorithm_minus_jeil": f"{algorithm_label} - Jeil",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    # Show the sample format only when Jeil baseline values are not loaded.
    # Once Program_run/JeilYardUtilization.csv exists, the extra guide table just adds noise.
    if comparison["jeil_avg_utilization"].isna().all():
        st.markdown("#### Expected Jeil baseline CSV format")
        sample = pd.DataFrame({
            "yard_name": ["A01", "A02", "B01"],
            "jeil_avg_utilization": [0.512, 0.487, 0.268],
        })
        st.dataframe(sample, use_container_width=True, hide_index=True)
        st.caption(f"Place this file in the selected result folder as {FIELD_UTILIZATION_FILE}. Values can be 0.512, 51.2, or 51.2%.")


def render_field_utilization_map(
    yards_df: pd.DataFrame,
    field_df: pd.DataFrame,
    selected_yard: str,
) -> None:
    yard_day = yards_df.copy()
    yard_day["usage"] = 0.0
    yard_day["utilization"] = 0.0
    yard_day["over_capacity"] = False
    boxes = build_diagram_boxes(yard_day)

    field_by_yard = (
        field_df.set_index("yard_name")["jeil_avg_utilization"].to_dict()
        if not field_df.empty
        else {}
    )
    max_utilization = max((float(value) for value in field_by_yard.values()), default=0.0)

    fig = go.Figure()
    add_factory_areas(fig)
    hover_text = []

    for _, row in boxes.iterrows():
        yard_name = row["yard_name"]
        utilization = float(field_by_yard.get(yard_name, 0.0) or 0.0)
        ratio = utilization / max_utilization if max_utilization > 0 else 0.0
        alpha = 0.12 + 0.72 * ratio if utilization > 0 else 0.08
        is_selected = yard_name == selected_yard

        fig.add_shape(
            type="rect",
            x0=row["x0"], y0=row["y0"], x1=row["x1"], y1=row["y1"],
            fillcolor=f"rgba(22, 163, 74, {alpha:.2f})",
            line=dict(
                color="#dc2626" if is_selected else "#16a34a",
                width=3 if is_selected else 1.5,
            ),
            layer="above",
        )
        hover_text.append(
            "<br>".join([
                f"<b>{yard_name}</b>",
                f"Jeil avg utilization: {utilization:.1%}",
            ])
        )

    fig.add_trace(go.Scatter(
        x=boxes["cx"], y=boxes["cy"],
        mode="markers+text",
        text=["<b>" + name + "</b>" for name in boxes["yard_name"]],
        textposition="middle center",
        textfont=dict(size=10, color="#0f172a"),
        marker=dict(size=24, color="rgba(255,255,255,0.01)"),
        hovertext=hover_text,
        hoverinfo="text",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="markers",
        marker=dict(size=12, color="rgba(22, 163, 74, 0.72)"),
        name="Jeil Technos avg utilization",
    ))

    fig.update_layout(
        width=int(YARD_DIAGRAM_WIDTH * YARD_DIAGRAM_SCALE),
        height=int(YARD_DIAGRAM_HEIGHT * YARD_DIAGRAM_SCALE),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            font=dict(color="#0f172a"),
        ),
    )
    fig.update_xaxes(visible=False, range=[0, YARD_DIAGRAM_WIDTH], constrain="domain", fixedrange=True)
    fig.update_yaxes(visible=False, range=[YARD_DIAGRAM_HEIGHT, 0], scaleanchor="x", scaleratio=1, fixedrange=True)

    st.markdown('<div class="yard-diagram-scroll">', unsafe_allow_html=True)
    st.plotly_chart(
        fig,
        use_container_width=False,
        config=PLOTLY_LOCKED_CONFIG,
        key="field_utilization_map",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_field_utilization_table(yards_df: pd.DataFrame, field_df: pd.DataFrame) -> None:
    if field_df.empty:
        st.info("No Jeil Technos utilization data is available.")
        return

    display = (
        yards_df[["yard_name", "block"]]
        .merge(field_df, on="yard_name", how="left")
        .groupby("block", as_index=False)
        .agg(jeil_avg_utilization=("jeil_avg_utilization", "mean"))
        .sort_values("block")
    )
    display["jeil_avg_utilization"] = display["jeil_avg_utilization"].map(
        lambda value: "-" if pd.isna(value) else f"{value:.1%}"
    )
    display = display.rename(columns={
        "block": "block",
        "jeil_avg_utilization": "Jeil avg utilization",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)


def render_objective_term_comparison(comparison: pd.DataFrame) -> None:
    if comparison.empty:
        st.info("No objective term summary is available.")
        return

    display = comparison.copy()

    def format_term_value(value) -> str:
        if pd.isna(value):
            return "-"
        numeric = float(value)
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:,.1f}"

    source_columns = [
        column for column in comparison.columns
        if column not in ["항목", "term"]
    ]
    for source in source_columns:
        if source in display.columns:
            display[source] = display[source].map(format_term_value)

    st.markdown(
        '<p class="section-title">Objective Term Comparison - 7,805 Packings</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        display[["항목", "term"] + source_columns],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "동일한 7,805개 packing을 대상으로 비교했습니다. "
        "LNS 2,000회, 기본 가중치 200, 1, 1, 1을 적용했으며 "
        "W0/W500/W2000은 Project Code 가중치만 다릅니다."
    )


def render_v3_weight_comparison(comparison: pd.DataFrame) -> None:
    if comparison.empty:
        st.info("No v3 project-code-weight experiment summary is available.")
        return

    term_rows = [
        ("Project Code penalty", "project_mixing_penalty"),
        ("여러 Project Code가 배정된 Yard 수", "mixed_yards"),
        ("여러 Project Code가 함께 존재한 Yard-day 수", "mixed_yard_days"),
        ("동일 Yard-day의 최대 Project Code 수", "max_project_codes_in_same_yard_day"),
        ("한 번 이상 사용한 Yard 수", "used_yards"),
        ("실행시간 (초)", "runtime_sec"),
    ]

    weight_columns = [
        f"W{int(weight)}"
        for weight in comparison["mixing_weight"].tolist()
    ]
    rows = []
    for term_label, term_key in term_rows:
        row = {"항목": term_label, "term": term_key}
        for _, result in comparison.iterrows():
            weight_column = f"W{int(result['mixing_weight'])}"
            value = result[term_key]
            if pd.isna(value):
                row[weight_column] = "-"
            elif float(value).is_integer():
                row[weight_column] = f"{int(value):,}"
            else:
                row[weight_column] = f"{float(value):,.1f}"
        rows.append(row)

    display = pd.DataFrame(rows)

    st.markdown(
        '<p class="section-title">Project Code Weight Comparison - 7,805 Packings</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        display[["항목", "term"] + weight_columns],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "LNS 2,000회, 기본 가중치 200, 1, 1, 1. "
        "Project Code 가중치 0 / 500 / 2,000 비교."
    )


def render_jeil_project_usage_sample() -> None:
    st.markdown("#### Expected Jeil project-yard CSV format")
    sample = pd.DataFrame({
        "project_code": ["2411039", "2411039", "2502023"],
        "yard_name": ["A01", "D09", "H14"],
        "packing_count": [12, 8, 21],
    })
    st.dataframe(sample, use_container_width=True, hide_index=True)
    st.caption(f"Place this file in the selected result folder as {JEIL_PROJECT_YARD_FILE}.")


def choose_project_code_from_usage(usage_df: pd.DataFrame, label_prefix: str = "") -> str:
    project_stats = build_project_stats(usage_df)
    if project_stats.empty:
        return ""

    project_labels = {
        row["project_code"]: f"{row['project_code']} ({int(row['yard_count'])} yards, {int(row['total_number'])} packings)"
        for _, row in project_stats.iterrows()
    }
    query = st.text_input(f"{label_prefix}Search project code", value="", placeholder="e.g. 2502023")
    project_options = project_stats["project_code"].astype(str).tolist()
    if query:
        project_options = [code for code in project_options if query.lower() in code.lower()]

    if not project_options:
        st.warning("No project code matches the search.")
        return ""

    return st.selectbox(
        f"{label_prefix}Project code",
        project_options,
        format_func=lambda code: project_labels.get(code, code),
    )


def shift_selected_day(delta: int, min_day: int, max_day: int) -> None:
    current_day = int(st.session_state.get("selected_day_filter", min_day))
    st.session_state["selected_day_filter"] = max(
        min_day,
        min(max_day, current_day + delta),
    )


def main() -> None:
    st.set_page_config(page_title="JeilTechnos Yard Map", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("JeilTechnos Yard Map")
    st.caption(
        "현업 배치와 Project Code 가중치 0 / 500 / 2,000 결과를 "
        "동일한 MES 유효 packing 7,805개 기준으로 비교합니다."
    )

    with st.sidebar:
        st.header("Input")
        program_run_dir = st.text_input("Result folder", value=str(PROGRAM_RUN_DIR))
        if st.button("Reload data"):
            st.cache_data.clear()

        available_result_sets = []
        for label, files in ALGORITHM_RESULT_SETS:
            daily_exists = (Path(program_run_dir) / files["daily"]).exists()
            assign_exists = (Path(program_run_dir) / files["assign"]).exists()
            if daily_exists or assign_exists:
                available_result_sets.append((label, files))

        if not available_result_sets:
            st.error("No algorithm result files were found in the selected result folder.")
            return

        selected_source_label = st.selectbox(
            "Data source",
            [FIELD_SOURCE_LABEL] + [label for label, _ in available_result_sets],
            index=0,
        )
        is_field_source = selected_source_label == FIELD_SOURCE_LABEL
        selected_result_label = (
            available_result_sets[0][0]
            if is_field_source
            else selected_source_label
        )
        selected_result_files = dict(available_result_sets)[selected_result_label]
        selected_algorithm_label = selected_result_label
        if is_field_source:
            st.caption(
                f"utilization={FIELD_UTILIZATION_FILE} / "
                f"project-yard={JEIL_PROJECT_YARD_FILE}"
            )
        else:
            st.caption(
                f"daily={selected_result_files['daily']} / "
                f"assignment={selected_result_files['assign']}"
            )

    daily_df = load_daily_placement(program_run_dir, selected_result_files["daily"])
    yards_df = load_yard_config(program_run_dir)
    assign_df = load_assignment_result(program_run_dir, selected_result_files["assign"])
    field_df = load_field_utilization(program_run_dir)
    jeil_project_usage_df = load_jeil_project_yard_usage(program_run_dir)
    objective_term_comparison = load_objective_term_comparison(program_run_dir)
    v3_weight_comparison = load_v3_weight_comparison(program_run_dir)
    if daily_df.empty or yards_df.empty:
        return

    min_day = int(daily_df["day"].min())
    max_day = int(daily_df["day"].max())

    with st.sidebar:
        st.header("View")
        view_options = ["Utilization comparison", "Project yard usage"]
        if not is_field_source:
            view_options += ["Daily stacking board", "Selected yard detail"]
        view_mode = st.radio(
            "Mode",
            view_options,
            index=0,
        )

        st.header("Filter")
        selected_day = min_day
        if not is_field_source:
            if "selected_day_filter" not in st.session_state:
                st.session_state["selected_day_filter"] = min_day
            else:
                st.session_state["selected_day_filter"] = max(
                    min_day,
                    min(max_day, int(st.session_state["selected_day_filter"])),
                )

            st.markdown("**Day**")
            previous_col, slider_col, next_col = st.columns([1, 5, 1])
            with previous_col:
                st.button(
                    "−",
                    key="previous_day_button",
                    use_container_width=True,
                    on_click=shift_selected_day,
                    args=(-1, min_day, max_day),
                )
            with slider_col:
                selected_day = st.slider(
                    "Day",
                    min_value=min_day,
                    max_value=max_day,
                    key="selected_day_filter",
                    label_visibility="collapsed",
                )
            with next_col:
                st.button(
                    "＋",
                    key="next_day_button",
                    use_container_width=True,
                    on_click=shift_selected_day,
                    args=(1, min_day, max_day),
                )
            st.caption(f"date: {day_to_date_label(selected_day)}")
        yard_names = sorted(yards_df["yard_name"].astype(str).tolist(), key=yard_sort_key)
        selected_yard = st.selectbox("Selected yard", yard_names, index=0)

    yard_day = build_yard_day(daily_df, yards_df, selected_day)
    selected_yard_config = yards_df[yards_df["yard_name"] == selected_yard].iloc[0]
    selected_active = get_packings_for_yard_day(daily_df, selected_yard, selected_day)

    if view_mode == "Utilization comparison":
        st.markdown('<p class="section-title">Average Utilization Comparison</p>', unsafe_allow_html=True)
        if is_field_source:
            render_field_utilization_map(yards_df, field_df, selected_yard)
            render_field_utilization_table(yards_df, field_df)
            render_objective_term_comparison(objective_term_comparison)
            render_v3_weight_comparison(v3_weight_comparison)
        else:
            comparison = build_utilization_comparison(daily_df, yards_df, field_df)
            if field_df.empty:
                st.warning(
                    f"Jeil baseline file is not loaded yet. Add {FIELD_UTILIZATION_FILE} to the selected result folder "
                    "to compare Jeil Technos and algorithm utilization."
                )
            render_utilization_comparison_map(
                yards_df,
                comparison,
                selected_yard,
                selected_algorithm_label,
            )
            render_utilization_comparison_table(comparison, selected_algorithm_label)

    elif view_mode == "Project yard usage":
        with st.sidebar:
            st.header("Project")
            project_source = "Jeil Technos"
            algorithm_basis = "Final assignment"
            if not is_field_source:
                project_source = st.radio(
                    "Source",
                    [selected_algorithm_label, "Jeil Technos", "Compare side-by-side"],
                    index=0,
                )
                algorithm_basis = st.radio("Algorithm basis", ["Final assignment", "Daily active"], index=0)
            heatmap = st.checkbox("Color yards by packing count", value=True)

        algorithm_usage_df = build_project_yard_usage(daily_df, assign_df, algorithm_basis, selected_day)
        if project_source == selected_algorithm_label:
            option_usage_df = algorithm_usage_df
        elif project_source == "Jeil Technos":
            option_usage_df = jeil_project_usage_df
        else:
            option_usage_df = pd.concat([algorithm_usage_df, jeil_project_usage_df], ignore_index=True)

        if option_usage_df.empty:
            st.info("No project-yard usage data is available for the selected source.")
            if project_source != selected_algorithm_label:
                render_jeil_project_usage_sample()
        else:
            selected_project = choose_project_code_from_usage(option_usage_df)
            if selected_project:
                if project_source == selected_algorithm_label:
                    render_project_yard_map(
                        yards_df,
                        yard_day,
                        algorithm_usage_df,
                        selected_project,
                        selected_yard,
                        heatmap,
                        chart_key="algorithm_project_yard_diagram",
                        source_label=selected_algorithm_label,
                    )
                elif project_source == "Jeil Technos":
                    if jeil_project_usage_df.empty:
                        st.warning(f"Jeil project-yard file is not loaded yet. Add {JEIL_PROJECT_YARD_FILE} to the selected result folder.")
                        render_jeil_project_usage_sample()
                    render_project_yard_map(
                        yards_df,
                        yard_day,
                        jeil_project_usage_df,
                        selected_project,
                        selected_yard,
                        heatmap,
                        chart_key="jeil_project_yard_diagram",
                        source_label="Jeil Technos",
                    )
                else:
                    left, right = st.columns(2)
                    with left:
                        render_project_yard_map(
                            yards_df,
                            yard_day,
                            jeil_project_usage_df,
                            selected_project,
                            selected_yard,
                            heatmap,
                            chart_key="jeil_project_yard_diagram_compare",
                            source_label="Jeil Technos",
                        )
                        if jeil_project_usage_df.empty:
                            st.warning(f"Jeil project-yard file is not loaded yet. Add {JEIL_PROJECT_YARD_FILE} to the selected result folder.")
                            render_jeil_project_usage_sample()
                    with right:
                        render_project_yard_map(
                            yards_df,
                            yard_day,
                            algorithm_usage_df,
                            selected_project,
                            selected_yard,
                            heatmap,
                            chart_key="algorithm_project_yard_diagram_compare",
                            source_label=selected_algorithm_label,
                        )

    elif view_mode == "Daily stacking board":
        st.markdown('<p class="section-title">Daily Slot / Level Board</p>', unsafe_allow_html=True)
        with st.sidebar:
            st.header("Stack Board")
            block_options = sorted(yards_df["block"].dropna().astype(str).unique().tolist())
            default_blocks = [block for block in block_options if block != "J"]
            selected_blocks = st.multiselect("Blocks", block_options, default=default_blocks)

            stack_yards_df = yards_df.copy()
            if selected_blocks:
                stack_yards_df = stack_yards_df[stack_yards_df["block"].isin(selected_blocks)]
            stack_yard_options = sorted(stack_yards_df["yard_name"].astype(str).tolist(), key=yard_sort_key)
            day_active_yards = sorted(
                daily_df[daily_df["day"] == selected_day]["yard_name"].dropna().astype(str).unique().tolist(),
                key=yard_sort_key,
            )
            ordered_stack_yards = [y for y in day_active_yards if y in stack_yard_options]
            ordered_stack_yards += [y for y in stack_yard_options if y not in set(ordered_stack_yards)]
            if not ordered_stack_yards:
                st.warning("No yards match the selected blocks.")
                return

            default_focus = selected_yard if selected_yard in ordered_stack_yards else ordered_stack_yards[0]
            focus_yard = st.selectbox(
                "Focus yard",
                ordered_stack_yards,
                index=ordered_stack_yards.index(default_focus),
            )
            color_by = st.selectbox("Color by", ["project_code", "group_id"], index=0)
            show_overview_cards = st.checkbox("Show overview cards", value=True)
            show_empty_yards = st.checkbox("Show empty yards in overview", value=False)
            max_overview_yards = len(ordered_stack_yards)
            max_yard_cards = st.slider(
                "Max overview yards",
                min_value=1,
                max_value=max_overview_yards,
                value=min(32, max_overview_yards),
                step=1,
            )

        st.caption("Focused yard board shows one yard clearly. Overview cards below are for scanning active yards on the same day.")
        render_daily_stacking_board(
            daily_df,
            yards_df,
            selected_day,
            selected_blocks,
            focus_yard,
            show_empty_yards,
            show_overview_cards,
            max_yard_cards,
            color_by,
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("active packings", len(selected_active))
        c2.metric("slot count", int(selected_yard_config.get("slot_count", 0) or 0))
        c3.metric("normal level", int(selected_yard_config.get("normal_level", 3) or 3))
        c4.metric("max level", int(selected_yard_config.get("max_level", 3) or 3))
        render_slot_grid(selected_active, selected_yard_config)
        st.dataframe(selected_active, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()










