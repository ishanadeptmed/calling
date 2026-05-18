import streamlit as st
from utils.transform_data import (
    process_facility_attendance
)

def app(go):

    st.title("Final Review")

    facility = st.session_state.get("facility")
    attendance_path = st.session_state.get("attendance_path")

    if not facility:
        st.error("No facility selected")
        return

    if not attendance_path:
        st.error("Attendance file missing")
        return

    # =========================================
    # PROCESS FINAL DATA
    # =========================================

    final_df = process_facility_attendance(
        facility=facility,
        attendance_file_path=attendance_path
    )

    # preview
    st.subheader("Processed Data Preview")

    st.dataframe(final_df)

    # =========================================
    # DOWNLOAD CSV
    # =========================================

    csv_data = final_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download Final CSV",
        data=csv_data,
        file_name=f"{facility}_final_processed.csv",
        mime="text/csv"
    )

    # =========================================
    # RESTART
    # =========================================

    if st.button("Restart"):
        st.session_state.clear()
        go("login")