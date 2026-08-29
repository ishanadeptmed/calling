import streamlit as st
import json
import pandas as pd
from supabase_client import supabase

from utils.storage_helpers import (
    load_dataframe_from_storage,
    load_care_level_rates,
    load_payer_rates
)

# =========================================================
# EXTRACTION HELPERS
# =========================================================

def get_unique_payers(df):
    """Extracts unique payers using the demographic Payer Name column."""
    if df is not None:
        for col in ["Payer Name", "payer"]:
            if col in df.columns:
                return df[col].dropna().unique().tolist()
    return []


def get_unique_care_levels(df):
    """Extracts unique care level characters from the PDPM HIPPS column."""
    if df is not None and "PDPM HIPPS" in df.columns:
        # Use string slicing to extract character at index 2 (3rd character)
        extracted_levels = df["PDPM HIPPS"].astype(str).str[2].fillna('')
        return [level for level in extracted_levels.unique() if level.strip()]
    return []


# =========================================================
# STATE INITIALIZERS (Called by rates.py & payer_rates.py)
# =========================================================

def initialize_care_levels_state(facility: str, attendance_path: str):
    """Initializes st.session_state.care_rows for pages/rates.py"""
    if "care_rows" not in st.session_state:
        st.session_state.care_rows = []
        
        existing_rates = load_care_level_rates(facility)
        if existing_rates:
            for level, cost in existing_rates.items():
                st.session_state.care_rows.append({
                    "care_level": level,
                    "cost": float(cost)
                })
        else:
            attendance_df = load_dataframe_from_storage(attendance_path)
            unique_levels = get_unique_care_levels(attendance_df)
            if unique_levels:
                for level in unique_levels:
                    st.session_state.care_rows.append({
                        "care_level": str(level),
                        "cost": 0.0
                    })
            else:
                st.session_state.care_rows.append({
                    "care_level": "",
                    "cost": 0.0
                })


def initialize_payer_rates_state(facility: str, attendance_path: str):
    """Initializes st.session_state.payer_rows for pages/payer_rates.py"""
    if "payer_rows" not in st.session_state:
        st.session_state.payer_rows = []
        
        existing_payers = load_payer_rates(facility)
        raw_df = load_dataframe_from_storage(attendance_path)
        unique_payers = get_unique_payers(raw_df)
            
        if unique_payers:
            for payer in unique_payers:
                payer_clean = str(payer).strip()
                saved_rate = existing_payers.get(payer_clean.lower(), 0.0)
                st.session_state.payer_rows.append({
                    "payer": payer_clean,
                    "adjustment_percent": float(saved_rate)
                })
        else:
            for payer, rate in existing_payers.items():
                st.session_state.payer_rows.append({
                    "payer": payer.title(),
                    "adjustment_percent": float(rate)
                })


# =========================================================
# BACKEND DB PERSISTENCE (Called by rates.py & payer_rates.py)
# =========================================================

def save_care_level_rates_to_db(facility: str, care_rows: list):
    """Formats and uploads care level rate dictionary adjustments to Supabase."""
    formatted_data = [
        {"care_level": row["care_level"].strip(), "cost": float(row["cost"])}
        for row in care_rows if row["care_level"].strip()
    ]
    
    json_data = json.dumps(formatted_data, indent=4)
    file_path = f"{facility}/rates/care_level_rates.json"
    
    supabase.storage.from_("facility-data").upload(
        path=file_path,
        file=json_data.encode("utf-8"),
        file_options={"upsert": "true"}
    )


def save_payer_rates_to_db(facility: str, payer_rows: list):
    """Formats and uploads payer structural adjustments to Supabase."""
    formatted_data = [
        {"payer": row["payer"].strip(), "adjustment_percent": float(row["adjustment_percent"])}
        for row in payer_rows if row["payer"].strip()
    ]
    
    json_data = json.dumps(formatted_data, indent=4)
    file_path = f"{facility}/payer_rates/payer_rates.json"
    
    supabase.storage.from_("facility-data").upload(
        path=file_path,
        file=json_data.encode("utf-8"),
        file_options={"upsert": "true"}
    )


# =========================================================
# CORE PROCESSING ENGINE (Called by review_download.py)
# =========================================================

def process_facility_attendance(facility: str, attendance_file_path: str) -> pd.DataFrame:
    """
    Drops unneeded columns, extracts 'Care Level', sums 'A' markers across dates,
    groups duplicate entries by key demographics, and calculates financial fields.
    """
    # 1. Load raw data and config rules
    df = load_dataframe_from_storage(attendance_file_path).copy()
    care_rates = load_care_level_rates(facility)
    payer_adjustments = load_payer_rates(facility)

    # 2. Extract Care Level before dropping any data columns
    if 'PDPM HIPPS' in df.columns:
        df['Care Level'] = df['PDPM HIPPS'].astype(str).str[2]
        df['Care Level'] = df['Care Level'].fillna('-').replace(['','nan'],'-')
    else:
        df['Care Level'] = '-'

    # 3. Clean up explicitly specified layout columns
    columns_to_drop_set = {
        'Room', 'Room Rate', '# of Days', 'Action Code', 
        'Payer Code', 'Alt. Care Level'
    }
    demographic_columns = [
        'Resident Name', 'Resident Number', 'Payer Name', 'PDPM HIPPS', 'Care Level'
    ]

    actual_drop_list = [col for col in df.columns if col in columns_to_drop_set]
    df = df.drop(columns=actual_drop_list)

    # 4. Isolate date columns to scan and count 'A' markers
    date_columns = [col for col in df.columns if col not in demographic_columns]

    df['TotalDays'] = df[date_columns].apply(
        lambda row: row.astype(str).str.strip().str.upper().eq('A').sum(), 
        axis=1
    )

    # 5. Drop raw date columns before aggregation grouping
    df = df.drop(columns=date_columns)

    # 6. Groupby logic: Ensure 1 unique row representation per resident, payer, and care level
    groupby_keys = ['Resident Name', 'Resident Number', 'Payer Name', 'Care Level']
    existing_groupby_keys = [key for key in groupby_keys if key in df.columns]
    
    if existing_groupby_keys:
        agg_rules = {'TotalDays': 'sum'}
        if 'PDPM HIPPS' in df.columns and 'PDPM HIPPS' not in existing_groupby_keys:
            agg_rules['PDPM HIPPS'] = 'first'
            
        df = df.groupby(existing_groupby_keys, as_index=False).agg(agg_rules)

    # 7. Setup clean mapping operational lookup keys
    if "Payer Name" in df.columns:
        df["_payer_key"] = df["Payer Name"].astype(str).str.strip().str.lower()
    else:
        df["_payer_key"] = ""

    df["_care_key"] = df["Care Level"].astype(str).str.strip()

    # 8. Map JSON config values
    df["Base_Cost"] = df["_care_key"].map(care_rates).fillna(0.0)
    df["Adjustment_Percent"] = df["_payer_key"].map(payer_adjustments).fillna(0.0)
    
    # 9. Calculate Financial Columns
    df["Final_Cost"] = df["Base_Cost"] * df["Adjustment_Percent"]
    df["Total_Cost"] = df["TotalDays"] * df["Final_Cost"]
    # =========================================================
    # INJECT EXPLICIT SELECTION PARAMETERS FOR DASHBOARD TRACKING
    # =========================================================
    df["Year"] = str(st.session_state.get("upload_year", "2026"))
    df["Month"] = str(st.session_state.get("upload_month", "Unknown"))
    df["Facility"] = str(facility)

    # 10. Clean operational temporary layout variables
    drop_operational = ["_care_key", "_payer_key"]
    final_clean_cols = [col for col in drop_operational if col in df.columns]
    df = df.drop(columns=final_clean_cols)

    return df