import streamlit as st
from utils.transform_data import process_facility_attendance
# Import the native Streamlit dashboard utility component
from utils.dashboards import render_review_dashboard

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
    # 1. PROCESS FINAL DATA
    # =========================================

    final_df = process_facility_attendance(
        facility=facility,
        attendance_file_path=attendance_path
    )

    # =========================================
    # 2. PROCESSED DATA PREVIEW TABLE (TOP)
    # =========================================

    st.subheader("Processed Data Preview")

    st.dataframe(final_df)

    # =========================================
    # 3. DOWNLOAD CSV ACTIONS
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
    # 4. PERFORMANCE DASHBOARD VISUALS (SCROLL DOWN)
    # =========================================
    # Moved here so it renders underneath your main data assets
    render_review_dashboard(final_df)

    # =========================================
    # 5. RESTART ACTION
    # =========================================

    st.write("##") # Spacer before the restart utility
    if st.button("Restart"):
        st.session_state.clear()
        go("login")