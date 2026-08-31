import json

import duckdb
import pandas as pd
import streamlit as st

from supabase_client import supabase

from utils.storage_helpers import (
    load_dataframe_from_storage,
    load_care_level_rates,
    load_payer_rates,
)

def get_unique_payers(rel: duckdb.DuckDBPyRelation) -> list:
    """Extract unique payers using the demographic Payer Name column."""
    if rel is None:
        return []

    cols = list(rel.columns)

    for col in ["Payer Name", "payer"]:
        if col in cols:
            result = rel.query(
                "rel",
                f'''
                SELECT DISTINCT "{col}"
                FROM rel
                WHERE "{col}" IS NOT NULL
                '''
            ).fetchall()

            return [
                row[0]
                for row in result
                if row[0] is not None
            ]

    return []


def get_unique_care_levels(rel: duckdb.DuckDBPyRelation) -> list:
    """Extract unique care level characters from the PDPM HIPPS column."""
    if rel is None or "PDPM HIPPS" not in rel.columns:
        return []

    result = rel.query(
        "rel",
        """
        SELECT DISTINCT
            substr(
                CAST("PDPM HIPPS" AS VARCHAR),
                3,
                1
            ) AS care_level
        FROM rel
        WHERE trim(
            substr(
                CAST("PDPM HIPPS" AS VARCHAR),
                3,
                1
            )
        ) != ''
        AND substr(
            CAST("PDPM HIPPS" AS VARCHAR),
            3,
            1
        ) IS NOT NULL
        """
    ).fetchall()

    return [
        row[0]
        for row in result
        if row[0] and row[0].strip()
    ]

def initialize_care_levels_state(
    facility: str,
    attendance_path: str,
):
    """Initialize st.session_state.care_rows for pages/rates.py."""

    if "care_rows" not in st.session_state:
        st.session_state.care_rows = []

        existing_rates = load_care_level_rates(facility)

        if existing_rates:
            for level, cost in existing_rates.items():
                st.session_state.care_rows.append(
                    {
                        "care_level": level,
                        "cost": float(cost),
                    }
                )

        else:
            _con, attendance_rel = load_dataframe_from_storage(
                attendance_path
            )

            unique_levels = get_unique_care_levels(
                attendance_rel
            )

            if unique_levels:
                for level in unique_levels:
                    st.session_state.care_rows.append(
                        {
                            "care_level": str(level),
                            "cost": 0.0,
                        }
                    )
            else:
                st.session_state.care_rows.append(
                    {
                        "care_level": "",
                        "cost": 0.0,
                    }
                )


def initialize_payer_rates_state(
    facility: str,
    attendance_path: str,
):
    """Initialize st.session_state.payer_rows for pages/payer_rates.py."""

    if "payer_rows" not in st.session_state:
        st.session_state.payer_rows = []

        existing_payers = load_payer_rates(facility)

        _con, raw_rel = load_dataframe_from_storage(
            attendance_path
        )

        unique_payers = get_unique_payers(raw_rel)

        if unique_payers:
            for payer in unique_payers:
                payer_clean = str(payer).strip()

                saved_rate = existing_payers.get(
                    payer_clean.lower(),
                    0.0,
                )

                st.session_state.payer_rows.append(
                    {
                        "payer": payer_clean,
                        "adjustment_percent": float(
                            saved_rate
                        ),
                    }
                )

        else:
            for payer, rate in existing_payers.items():
                st.session_state.payer_rows.append(
                    {
                        "payer": payer.title(),
                        "adjustment_percent": float(rate),
                    }
                )

def save_care_level_rates_to_db(
    facility: str,
    care_rows: list,
):
    """Format and upload care level rates to Supabase."""

    formatted_data = [
        {
            "care_level": row["care_level"].strip(),
            "cost": float(row["cost"]),
        }
        for row in care_rows
        if row["care_level"].strip()
    ]

    json_data = json.dumps(
        formatted_data,
        indent=4,
    )

    file_path = (
        f"{facility}/rates/care_level_rates.json"
    )

    supabase.storage.from_("facility-data").upload(
        path=file_path,
        file=json_data.encode("utf-8"),
        file_options={"upsert": "true"},
    )


def save_payer_rates_to_db(
    facility: str,
    payer_rows: list,
):
    """Format and upload payer adjustments to Supabase."""

    formatted_data = [
        {
            "payer": row["payer"].strip(),
            "adjustment_percent": float(
                row["adjustment_percent"]
            ),
        }
        for row in payer_rows
        if row["payer"].strip()
    ]

    json_data = json.dumps(
        formatted_data,
        indent=4,
    )

    file_path = (
        f"{facility}/payer_rates/payer_rates.json"
    )

    supabase.storage.from_("facility-data").upload(
        path=file_path,
        file=json_data.encode("utf-8"),
        file_options={"upsert": "true"},
    )

COST_COLUMNS = [
    "Final_Cost",
    "Total_Cost",
]

COLUMNS_TO_DROP = {
    "Room",
    "Room Rate",
    "# of Days",
    "Action Code",
    "Payer Code",
    "Alt. Care Level",
}

DEMOGRAPHIC_COLUMNS = {
    "Resident Name",
    "Resident Number",
    "Payer Name",
    "PDPM HIPPS",
    "Care Level",
}


def process_facility_attendance(
    facility: str,
    attendance_file_path: str,
) -> pd.DataFrame:

    con, rel = load_dataframe_from_storage(
        attendance_file_path
    )

    care_rates = load_care_level_rates(
        facility
    )

    payer_adjustments = load_payer_rates(
        facility
    )

    con.register(
        "raw",
        rel,
    )

    all_cols = list(rel.columns)

    date_cols = [
        c
        for c in all_cols
        if c not in DEMOGRAPHIC_COLUMNS
        and c not in COLUMNS_TO_DROP
    ]

    if date_cols:
        a_count_exprs = " + ".join(
            f"""
            CASE
                WHEN upper(
                    trim(
                        CAST("{c}" AS VARCHAR)
                    )
                ) = 'A'
                THEN 1
                ELSE 0
            END
            """
            for c in date_cols
        )
    else:
        a_count_exprs = "0"

    has_hipps = "PDPM HIPPS" in all_cols
    has_payer = "Payer Name" in all_cols

    if has_hipps:
        care_level_expr = """
            substr(
                CAST("PDPM HIPPS" AS VARCHAR),
                3,
                1
            )
        """
    else:
        care_level_expr = "'-'"

    if has_payer:
        payer_key_expr = """
            lower(
                trim(
                    CAST("Payer Name" AS VARCHAR)
                )
            )
        """
    else:
        payer_key_expr = "''"

    # =====================================================
    # 5. BUILD DEMOGRAPHIC SELECT
    # =====================================================

    demographic_candidates = [
        "Resident Name",
        "Resident Number",
        "Payer Name",
        "PDPM HIPPS",
    ]

    select_demographics = [
        f'"{c}"'
        for c in demographic_candidates
        if c in all_cols
    ]

    stage1_select = []

    stage1_select.extend(
        select_demographics
    )

    stage1_select.append(
        f"""
        COALESCE(
            NULLIF(
                trim({care_level_expr}),
                ''
            ),
            '-'
        ) AS "Care Level"
        """
    )

    stage1_select.append(
        f"""
        ({a_count_exprs}) AS "TotalDays"
        """
    )

    stage1_sql = f"""
        SELECT
            {", ".join(stage1_select)}
        FROM raw
    """

    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE stage1 AS
        {stage1_sql}
        """
    )

    groupby_candidates = [
        "Resident Name",
        "Resident Number",
        "Payer Name",
        "Care Level",
    ]

    groupby_keys = [
        c
        for c in groupby_candidates
        if c in all_cols
        or c == "Care Level"
    ]

    group_clause = ", ".join(
        f'"{k}"'
        for k in groupby_keys
    )

    stage2_select = [
        f'"{k}"'
        for k in groupby_keys
    ]

    if has_hipps:
        stage2_select.append(
            'first("PDPM HIPPS") AS "PDPM HIPPS"'
        )

    stage2_select.append(
        'SUM("TotalDays") AS "TotalDays"'
    )

    stage2_sql = f"""
        SELECT
            {", ".join(stage2_select)}
        FROM stage1
        GROUP BY
            {group_clause}
    """

    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE stage2 AS
        {stage2_sql}
        """
    )

    if care_rates:
        care_df = pd.DataFrame(
            list(care_rates.items()),
            columns=[
                "_care_level",
                "_base_cost",
            ],
        )
    else:
        care_df = pd.DataFrame(
            columns=[
                "_care_level",
                "_base_cost",
            ]
        )
    if not care_df.empty:
        care_df["_care_level"] = (
            care_df["_care_level"]
            .astype(str)
            .str.strip()
        )

        care_df["_base_cost"] = pd.to_numeric(
            care_df["_base_cost"],
            errors="coerce",
        ).fillna(0.0)

    con.register(
        "care_lookup",
        care_df,
    )

    if payer_adjustments:
        payer_df = pd.DataFrame(
            list(payer_adjustments.items()),
            columns=[
                "_payer_key",
                "_adj_pct",
            ],
        )
    else:
        payer_df = pd.DataFrame(
            columns=[
                "_payer_key",
                "_adj_pct",
            ]
        )
    if not payer_df.empty:
        payer_df["_payer_key"] = (
            payer_df["_payer_key"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        payer_df["_adj_pct"] = pd.to_numeric(
            payer_df["_adj_pct"],
            errors="coerce",
        ).fillna(0.0)

    con.register(
        "payer_lookup",
        payer_df,
    )

    year_val = str(
        st.session_state.get(
            "upload_year",
            "2026",
        )
    )

    month_val = str(
        st.session_state.get(
            "upload_month",
            "Unknown",
        )
    )

    year_sql = year_val.replace(
        "'",
        "''",
    )

    month_sql = month_val.replace(
        "'",
        "''",
    )

    facility_sql = str(facility).replace(
        "'",
        "''",
    )

    if has_payer:
        payer_join = """
            lower(
                trim(
                    CAST(
                        s."Payer Name"
                        AS VARCHAR
                    )
                )
            ) = pl._payer_key
        """
    else:
        payer_join = "FALSE"


    stage3_sql = f"""
        SELECT
            s.*,

            ROUND(
                COALESCE(
                    cl._base_cost,
                    0.0
                ),
                2
            ) AS "Base_Cost",

            ROUND(
                COALESCE(
                    pl._adj_pct,
                    0.0
                ),
                2
            ) AS "Adjustment_Percent",

            ROUND(
                COALESCE(
                    cl._base_cost,
                    0.0
                )
                *
                (
                    1.0
                    +
                    COALESCE(
                        pl._adj_pct,
                        0.0
                    ) / 100.0
                ),
                2
            ) AS "Final_Cost",

            ROUND(
                s."TotalDays"
                *
                COALESCE(
                    cl._base_cost,
                    0.0
                )
                *
                (
                    1.0
                    +
                    COALESCE(
                        pl._adj_pct,
                        0.0
                    ) / 100.0
                ),
                2
            ) AS "Total_Cost",

            '{year_sql}' AS "Year",

            '{month_sql}' AS "Month",

            '{facility_sql}' AS "Facility"

        FROM stage2 s

        LEFT JOIN care_lookup cl
            ON trim(
                s."Care Level"
            ) = cl._care_level

        LEFT JOIN payer_lookup pl
            ON {payer_join}
    """


    result_df = con.execute(
        stage3_sql
    ).df()

    return result_df