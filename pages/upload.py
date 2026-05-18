import streamlit as st
from supabase_client import supabase

def app(go):

    st.title("Upload Files")

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

            st.success("Attendance uploaded successfully")

            go("rates")

        else:
            st.warning("Please upload attendance file")