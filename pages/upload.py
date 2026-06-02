import streamlit as st
from supabase_client import supabase

def app(go):
    st.title("Upload Files")

    # ---- YEAR & MONTH SELECTION SLICERS ----
    st.markdown("### **Select Processing Period**")
    col_yr, col_mo = st.columns(2)
    
    with col_yr:
        selected_year = st.selectbox(
            "Select Target Year", 
            options=["2024", "2025", "2026", "2027"], 
            index=2 # Defaults to 2026
        )
    with col_mo:
        selected_month = st.selectbox(
            "Select Target Month", 
            options=[
                "January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December"
            ]
        )

    st.write("---")

    attendance = st.file_uploader(
        "Attendance File",
        type=["csv", "xlsx"]
    )

    # ---------------- SAVE ----------------
    if st.button("Save Uploads"):
        facility = st.session_state.get("facility")

        if not facility:
            st.error("No facility selected")
            return

        if attendance:
            # Save selections directly to session state for backend transformer pipeline
            st.session_state.upload_year = selected_year
            st.session_state.upload_month = selected_month

            # preserve extension
            extension = attendance.name.split(".")[-1]
            file_path = f"{facility}/uploads/attendance.{extension}"

            # upload to supabase storage
            supabase.storage.from_("facility-data").upload(
                path=file_path,
                file=attendance.getvalue(),
                file_options={"upsert": "true"}
            )

            st.session_state.attendance_path = file_path
            st.success(f"Attendance for {selected_month} {selected_year} uploaded successfully!")

            go("rates")
        else:
            st.warning("Please upload attendance file")