import streamlit as st
import utils.transform_data as backbone

def app(go):
    st.title("Care Level Rates")

    facility = st.session_state.get("facility")
    attendance_path = st.session_state.get("attendance_path")

    if not facility or not attendance_path:
        st.error("Missing facility configuration environment parameters.")
        return

    # Let backbone prepare the session state arrays
    backbone.initialize_care_levels_state(facility, attendance_path)

    st.subheader("Configure Care Level Rates")

    for i, row in enumerate(st.session_state.care_rows):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            row["care_level"] = st.text_input("Care Level", value=row["care_level"], key=f"care_{i}")
        with col2:
            row["cost"] = st.number_input("Cost", value=float(row["cost"]), step=0.01, key=f"cost_{i}")
        with col3:
            if st.button("Delete", key=f"delete_{i}"):
                st.session_state.care_rows.pop(i)
                st.rerun()

    if st.button("Add Care Level"):
        st.session_state.care_rows.append({"care_level": "", "cost": 0.0})
        st.rerun()

    st.divider()

    if st.button("Save Rates"):
        try:
            # Send current data straight back to backbone for cloud persistence
            backbone.save_care_level_rates_to_db(facility, st.session_state.care_rows)
            st.success("Care level rates saved by Backbone!")
            go("payer_rates")
        except Exception as e:
            st.error(f"Save action rejected by backbone process: {e}")