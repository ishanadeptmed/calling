import streamlit as st
from supabase_client import supabase

def app(go):

    st.title("Facility Selection")

    user_email = st.session_state.user

    # ---------------- LOAD FACILITIES ----------------
    response = (
        supabase.table("facilities")
        .select("*")
        .eq("user_email", user_email)
        .execute()
    )

    facilities = [x["facility_name"] for x in response.data]

    # ---------------- ADD FACILITY ----------------
    new_facility = st.text_input("Add New Facility")

    if st.button("Add Facility"):

        if new_facility in facilities:
            st.warning("Facility already exists")
            
        elif new_facility:

            # save to database
            supabase.table("facilities").insert({
                "user_email": user_email,
                "facility_name": new_facility
            }).execute()

            # create folder in bucket
            folder_path = f"{user_email}/{new_facility}/.keep"

            supabase.storage.from_("facility-data").upload(
                path=folder_path,
                file=b""
            )

            st.success("Facility added")

            st.rerun()

    # ---------------- SELECT FACILITY ----------------
    if facilities:

        selected = st.selectbox("Select Facility", facilities)

        if st.button("Continue"):

            st.session_state.facility = selected

            go("upload")