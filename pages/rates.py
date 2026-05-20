import streamlit as st
import json

from supabase_client import supabase

from utils.storage_helpers import (
    load_care_level_rates,
    load_dataframe_from_storage
)

from utils.transform_data import (
    get_unique_care_levels
)


def app(go):

    st.title("Rates Configuration")

    facility = st.session_state.get("facility")

    if not facility:
        st.error("No facility selected")
        return

    attendance_path = st.session_state.get(
        "attendance_path"
    )

    if not attendance_path:
        st.error("Attendance file missing")
        return

    # =====================================
    # LOAD ATTENDANCE
    # =====================================

    attendance_df = load_dataframe_from_storage(
        attendance_path
    )

    unique_levels = get_unique_care_levels(
        attendance_df
    )

    # =====================================
    # LOAD SAVED RATES
    # =====================================

    existing_rates = load_care_level_rates(
        facility
    )

    # =====================================
    # INITIALIZE SESSION STATE
    # =====================================

    if "rate_rows" not in st.session_state:

        st.session_state.rate_rows = []

        for level in unique_levels:

            st.session_state.rate_rows.append({
                "care_level": level,
                "cost": float(
                    existing_rates.get(level, 0)
                )
            })

    st.subheader("Care Level Rates")

    # =====================================
    # EDITABLE TABLE
    # =====================================

    for i, row in enumerate(
        st.session_state.rate_rows
    ):

        col1, col2, col3 = st.columns(
            [3, 2, 1]
        )

        with col1:

            row["care_level"] = st.text_input(
                f"Care Level {i}",
                value=row["care_level"],
                key=f"care_{i}"
            )

        with col2:

            row["cost"] = st.number_input(
                f"Cost {i}",
                value=float(row["cost"]),
                step=1.0,
                key=f"cost_{i}"
            )

        with col3:

            if st.button(
                "Delete",
                key=f"delete_{i}"
            ):

                st.session_state.rate_rows.pop(i)

                st.rerun()

    # =====================================
    # ADD ROW
    # =====================================

    if st.button("Add Care Level"):

        st.session_state.rate_rows.append({
            "care_level": "",
            "cost": 0
        })

        st.rerun()

    st.divider()

    # =====================================
    # SAVE
    # =====================================

    if st.button("Save Rates"):

        rates_data = st.session_state.rate_rows

        json_data = json.dumps(
            rates_data,
            indent=4
        )

        file_path = (
            f"{facility}/rates/"
            "care_level_rates.json"
        )

        supabase.storage.from_(
            "facility-data"
        ).upload(
            path=file_path,
            file=json_data.encode("utf-8"),
            file_options={
                "upsert": "true"
            }
        )

        st.success(
            "Rates saved successfully"
        )

        go("payer_rates")