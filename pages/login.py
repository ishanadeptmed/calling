import streamlit as st
from supabase_client import supabase

def app(go):

    st.title("Login / Signup")

    mode = st.radio("Mode", ["Login", "Signup"])

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    # ---------------- SIGNUP ----------------
    if mode == "Signup":

        if st.button("Create Account"):

            try:
                response = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })

                st.success("Account created successfully")

            except Exception as e:
                st.error(f"Signup failed: {str(e)}")

    # ---------------- LOGIN ----------------
    else:

        if st.button("Login"):

            try:
                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                user = response.user

                if user:
                    st.session_state.user = user.email
                    st.success("Login successful")

                    go("facility")

            except Exception as e:
                st.error("Invalid login credentials")