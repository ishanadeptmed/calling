import json
from io import BytesIO
from typing import Dict, List

import pandas as pd
from supabase_client import supabase


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize dataframe column names.
    """

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace("#", "", regex=False)
    )

    return df

# =========================================================
# SUPABASE FILE HELPERS
# =========================================================

def download_file_from_supabase(path: str) -> bytes:
    """
    Download file bytes from Supabase bucket.
    """

    return (
        supabase.storage
        .from_("facility-data")
        .download(path)
    )



def load_dataframe_from_storage(path: str) -> pd.DataFrame:
    """
    Load CSV/XLSX file from Supabase bucket into dataframe.
    """

    file_bytes = download_file_from_supabase(path)

    if path.endswith(".csv"):

        return pd.read_csv(
            BytesIO(file_bytes),
            encoding="utf-8-sig"
        )

    elif path.endswith(".xlsx"):

        return pd.read_excel(BytesIO(file_bytes))

    else:
        raise ValueError("Unsupported file type")

# =========================================================
# LOAD FACILITY CONFIG JSONS
# =========================================================

def load_care_level_rates(facility: str) -> Dict[str, float]:
    """
    Load care level rates json.
    """

    path = f"{facility}/rates/care_level_rates.json"

    file_bytes = download_file_from_supabase(path)

    data = json.loads(file_bytes.decode("utf-8"))

    return {
        x["care_level"]: float(x["cost"])
        for x in data
    }

def load_payer_rates(facility: str) -> Dict[str, float]:
    """
    Load payer adjustment json.
    """

    path = f"{facility}/payer_rates/payer_rates.json"

    file_bytes = download_file_from_supabase(path)

    data = json.loads(file_bytes.decode("utf-8"))

    return {
        x["payer"]: float(x["adjustment_percent"])
        for x in data
    }

def transform_attendance_data(
    attendance_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Transform uploaded attendance report.
    """

    attendance_df = normalize_columns(attendance_df)

    # remove unnecessary columns
    columns_to_drop = [
        "room",
        "room_rate",
        "of_days",
        "action_code",
        "payer_code",
        "care_level",
        "alt_care_level"
    ]

    existing_drop_cols = [
        c for c in columns_to_drop
        if c in attendance_df.columns
    ]

    attendance_df = attendance_df.drop(
        columns=existing_drop_cols,
        errors="ignore"
    )

    demographic_columns = [
        "resident_name",
        "resident_number",
        "payer_name",
        "pdpm_hipps"
    ]

    # melt dates into rows
    df_long = pd.melt(
        attendance_df,
        id_vars=demographic_columns,
        var_name="date",
        value_name="attendance_status"
    )

    # A = 1 else 0
    df_long["total_days"] = (
        df_long["attendance_status"]
        .map({"A": 1})
        .fillna(0)
        .astype(int)
    )

    # summarize
    group_keys = [
        "resident_name",
        "resident_number",
        "payer_name",
        "pdpm_hipps"
    ]

    df_long = (
        df_long
        .groupby(group_keys, as_index=False)["total_days"]
        .sum()
    )

    # extract care level
    df_long["care_level"] = (
        df_long["pdpm_hipps"]
        .astype(str)
        .str[2]
        .fillna("")
    )

    return df_long


# =========================================================
# COST CALCULATIONS
# =========================================================

def apply_care_level_rates(
    df: pd.DataFrame,
    rate_map: Dict[str, float]
) -> pd.DataFrame:
    """
    Apply daily care level rates.
    """

    df = df.copy()

    df["daily_cost"] = (
        df["care_level"]
        .map(rate_map)
        .fillna(0.0)
        .astype(float)
    )

    df["total_cost"] = (
        df["total_days"] * df["daily_cost"]
    ).astype(float)

    return df

def apply_payer_adjustments(
    df: pd.DataFrame,
    payer_map: Dict[str, float]
) -> pd.DataFrame:
    """
    Apply payer adjustment multipliers.
    """

    df = df.copy()

    normalized_payer_map = {
        str(k).strip().lower(): float(v)
        for k, v in payer_map.items()
    }

    df["payer_name_normalized"] = (
        df["payer_name"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["payer_multiplier"] = (
        df["payer_name_normalized"]
        .map(normalized_payer_map)
        .fillna(1.0)
    )

    df["updated_total_cost"] = (
        df["total_cost"] * df["payer_multiplier"]
    ).astype(float)

    return df

# =========================================================
# MAIN PIPELINE
# =========================================================

def process_facility_attendance(
    facility: str,
    attendance_file_path: str
) -> pd.DataFrame:
    """
    Full end-to-end pipeline.

    1. Load uploaded attendance file
    2. Transform attendance
    3. Load care level config
    4. Load payer config
    5. Apply all calculations
    6. Return final dataframe
    """

    # load uploaded attendance
    attendance_df = load_dataframe_from_storage(
        attendance_file_path
    )

    # load facility configs
    care_level_rates = load_care_level_rates(facility)

    payer_rates = load_payer_rates(facility)

    # transform attendance
    df = transform_attendance_data(attendance_df)

    # apply care level rates
    df = apply_care_level_rates(
        df,
        care_level_rates
    )

    # apply payer adjustments
    df = apply_payer_adjustments(
        df,
        payer_rates
    )

    # add facility
    df["facility"] = facility

    return df


# =========================================================
# EXPORT HELPERS
# =========================================================

def upload_processed_dataframe(
    df: pd.DataFrame,
    facility: str,
    filename: str = "final_processed_data.csv"
):
    """
    Upload processed dataframe back to Supabase.
    """

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    path = f"{facility}/exports/{filename}"

    supabase.storage.from_("facility-data").upload(
        path=path,
        file=csv_bytes,
        file_options={"upsert": "true"}
    )


# =========================================================
# DATABASE HELPERS
# =========================================================

def save_dataframe_to_postgres(
    df: pd.DataFrame,
    table_name: str,
    engine
):
    """
    Save dataframe into postgres.
    """

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False
    )

# =========================================================
# FETCH UNIQUE PAYERS
# =========================================================

def get_unique_payers(
    attendance_df: pd.DataFrame
) -> List[str]:
    """
    Extract unique payers.
    """

    attendance_df = normalize_columns(attendance_df)

    if "payer_name" not in attendance_df.columns:
        return []

    return sorted(
        attendance_df["payer_name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


# =========================================================
# FETCH UNIQUE CARE LEVELS
# =========================================================

def get_unique_care_levels(
    attendance_df: pd.DataFrame
) -> List[str]:
    """
    Extract care levels from PDPM HIPPS.
    """

    attendance_df = normalize_columns(attendance_df)

    if "pdpm_hipps" not in attendance_df.columns:
        return []

    care_levels = (
        attendance_df["pdpm_hipps"]
        .astype(str)
        .str[2]
        .dropna()
        .unique()
        .tolist()
    )

    return sorted(care_levels)