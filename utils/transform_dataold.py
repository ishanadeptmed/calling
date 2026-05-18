from __future__ import annotations

import pandas as pd
from pandas import DataFrame
from typing import Optional, Sequence

from services.ratemap_service import apply_rate_map

# ---------------------------
# Constants
# ---------------------------
ID_COLUMNS: list[str] = [
    "resident_name",
    "resident_number",
    "payer_name",
    "pdpm_hipps",
]

DROP_COLUMNS: list[str] = [
    "Room",
    "Room Rate",
    "# of Days",
    "Action Code",
    "Payer Code",
    "Care Level",
    "Alt. Care Level",
]

ATTENDANCE_MAP: dict[str, int] = {
    "A": 1,
}

# ---------------------------
# Core Utilities
# ---------------------------
def normalize_columns(df: DataFrame) -> DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    column_mapping = {
        "Resident Name": "resident_name",
        "Resident Number": "resident_number",
        "Payer Name": "payer_name",
        "PDPM HIPPS": "pdpm_hipps",
    }

    return df.rename(columns=column_mapping)


def validate_required_columns(df: DataFrame, required_columns: Sequence[str]) -> None:
    """Raise ValueError if required columns are missing."""
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in file: {missing}")


def get_date_columns(
    df: DataFrame,
    id_columns: Optional[Sequence[str]] = None,
    extra_id_columns: Optional[Sequence[str]] = None,
) -> list[str]:
    """Detect all date columns using common date formats."""
    id_cols = list(id_columns or ID_COLUMNS)
    if extra_id_columns:
        id_cols += list(extra_id_columns)

    date_cols: list[str] = []
    for col in df.columns:
        col_str = str(col).strip()
        if col_str.lower() in {name.lower() for name in id_cols}:
            continue

        parsed = pd.to_datetime(col_str, errors="coerce", dayfirst=False)
        if pd.notna(parsed):
            date_cols.append(col)

    if not date_cols:
        date_cols = [col for col in df.columns if str(col).strip() not in id_cols]

    return date_cols


# ---------------------------
# Transformation Helpers
# ---------------------------
def melt_attendance(
    df: DataFrame,
    id_columns: Optional[list[str]] = None,
    extra_id_columns: Optional[list[str]] = None,
    value_name: str = "present",
) -> DataFrame:
    """Convert wide attendance table into row-wise records."""
    df = normalize_columns(df)
    validate_required_columns(df, id_columns or ID_COLUMNS)

    date_cols = get_date_columns(df, id_columns, extra_id_columns)
    if not date_cols:
        raise ValueError("No date columns found in attendance sheet")

    id_vars = list(id_columns or ID_COLUMNS)
    if extra_id_columns:
        id_vars += extra_id_columns

    return df.melt(
        id_vars=id_vars,
        value_vars=date_cols,
        var_name="date",
        value_name=value_name,
    )


def add_amount(
    df: DataFrame,
    value_col: str = "present",
    rate_col: str = "rate",
    amount_col: str = "amount",
) -> DataFrame:
    """Calculate amount as present days times rate."""
    df = df.copy()

    df[value_col] = (
        df[value_col]
        .astype(str)
        .str.split("-")
        .str[0]
    )
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)

    if rate_col not in df.columns:
        df[rate_col] = 0.0
    else:
        df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce").fillna(0.0)

    if df[value_col].isna().all():
        raise ValueError("Present column could not be parsed into numeric values")

    df[amount_col] = df[value_col] * df[rate_col]
    return df


def count_status(
    df: DataFrame,
    status_value: str = "A",
    date_start_idx: int = 10,
    output_col: str = "num_of_days",
) -> DataFrame:
    """Count occurrences of status_value across date columns."""
    df = df.copy()
    cols_to_sum = df.iloc[:, date_start_idx:]
    df[output_col] = (cols_to_sum == status_value).sum(axis=1).astype(int)
    return df

# ---------------------------
# Summary / Rate Calculations
# ---------------------------
def summarize_present_a(
    census_df: DataFrame,
    resident_df: DataFrame,
    rates_df: DataFrame,
    venue_df: Optional[DataFrame] = None,
    status_value: str = "A",
) -> DataFrame:
    """Summarize attendance, map care level rates, and calculate total cost."""
    census_df = census_df.copy()
    resident_df = resident_df.copy()
    rates_df = rates_df.copy()

    census_df.columns = census_df.columns.str.strip()
    resident_df.columns = resident_df.columns.str.strip()
    rates_df.columns = rates_df.columns.str.strip()

    if "census_value" in census_df.columns:
        census_filtered = census_df[census_df["census_value"] == status_value].copy()
    elif "present" in census_df.columns:
        census_filtered = census_df[census_df["present"] == 1].copy()
    else:
        raise ValueError("Attendance data must contain 'census_value' or 'present' column")

    if "Resident Number" in resident_df.columns:
        merge_key = "Resident Number"
    elif "resident_number" in resident_df.columns:
        merge_key = "resident_number"
    else:
        raise ValueError("Resident data must contain Resident Number column")

    merged = census_filtered.merge(
        resident_df,
        left_on="resident_number",
        right_on=merge_key,
        how="left",
    )

    group_keys = [
        "Resident Name" if "Resident Name" in merged.columns else "resident_name",
        "Resident Number" if "Resident Number" in merged.columns else "resident_number",
        "Payer Name" if "Payer Name" in merged.columns else "payer_name",
        "PDPM HIPPS" if "PDPM HIPPS" in merged.columns else "pdpm_hipps",
    ]

    summary = merged.groupby(group_keys).size().reset_index(name="total_days")

    summary = summary.rename(columns={
        group_keys[0]: "resident_name",
        group_keys[1]: "resident_number",
        group_keys[2]: "payer_name",
        group_keys[3]: "pdpm_hipps",
    })

    summary["pdpm_hipps"] = summary["pdpm_hipps"].astype(str).fillna("")
    summary["pdpm_3rd_char"] = summary["pdpm_hipps"].str[2].fillna("")

    rate_map = dict(
        zip(
            rates_df["care_level"].astype(str),
            pd.to_numeric(rates_df["rate"], errors="coerce").fillna(0.0),
        )
    )

    summary["base_rate"] = summary["pdpm_3rd_char"].map(rate_map).fillna(0.0).astype(float)

    if venue_df is not None and not venue_df.empty:
        venue_df = venue_df.copy()
        venue_df.columns = venue_df.columns.str.strip()
        venue_map = dict(
            zip(
                venue_df["Payer"].astype(str),
                pd.to_numeric(venue_df["rate_exchange"], errors="coerce").fillna(1.0),
            )
        )
        summary["rate_exchange"] = summary["payer_name"].astype(str).map(venue_map).fillna(1.0)
    else:
        summary["rate_exchange"] = 1.0

    summary["updated_rate"] = (
        summary["base_rate"].astype(float)
        * summary["rate_exchange"].astype(float)
    )
    summary["total_cost"] = (
        summary["total_days"].astype(float)
        * summary["updated_rate"]
    )

    return summary


def payer_list_from_summary(df_summary: DataFrame) -> list[str]:
    """Return sorted unique payer names from summary."""
    validate_required_columns(df_summary, ["payer_name"])
    return sorted(df_summary["payer_name"].dropna().astype(str).unique())