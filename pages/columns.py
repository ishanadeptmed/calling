import streamlit as st
import pandas as pd

def app(go):

    st.title("Column Review")

    df = pd.read_csv(st.session_state.attendance_path)

    st.session_state.column_map = {}

    for col in df.columns:
        action = st.radio(
            col,
            ["Keep", "Drop", "Date Column"],
            key=col
        )
        st.session_state.column_map[col] = action

    if st.button("Next"):
        go("rates")