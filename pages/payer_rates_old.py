import streamlit as st
import json

from supabase_client import supabase

from utils.transform_data import (
    load_dataframe_from_storage,
    get_unique_payers
)

def app(go):

    st.title("Payer Rates")

    facility = st.session_state.get("facility")

    attendance_path = st.session_state.get("attendance_path")

    if not facility:
        st.error("No facility selected")
        return

    if not attendance_path:
        st.error("Attendance file not uploaded")
        return

    # ============================================
    # LOAD ATTENDANCE FILE
    # ============================================

    attendance_df = load_dataframe_from_storage(
        attendance_path
    )

    unique_payers = get_unique_payers(
        attendance_df
    )

    # ============================================
    # INITIALIZE SESSION STATE
    # ============================================

    if "payer_rows" not in st.session_state:

        st.session_state.payer_rows = [
            {
                "payer": payer,
                "adjustment_percent": 1.0
            }
            for payer in unique_payers
        ]

    # ============================================
    # PAGE UI
    # ============================================

    st.subheader("Payer Adjustment Rates")

    for i, row in enumerate(st.session_state.payer_rows):

        col1, col2 = st.columns([4, 2])

        # payer name
        with col1:

            st.text_input(
                f"Payer {i}",
                value=row["payer"],
                disabled=True,
                key=f"payer_{i}"
            )

        # adjustment %
        with col2:

            row["adjustment_percent"] = st.number_input(
                f"Adjustment %",
                value=float(row["adjustment_percent"]),
                step=0.01,
                key=f"adjustment_{i}"
            )

    st.divider()

    # ============================================
    # SAVE JSON
    # ============================================

    if st.button("Save Payer Rates"):

        payer_data = st.session_state.payer_rows

        json_data = json.dumps(
            payer_data,
            indent=4
        )

        file_path = (
            f"{facility}/payer_rates/"
            f"payer_rates.json"
        )

        supabase.storage.from_("facility-data").upload(
            path=file_path,
            file=json_data.encode("utf-8"),
            file_options={"upsert": "true"}
        )

        st.success(
            "Payer rates saved successfully"
        )

        go("review")