import streamlit as st
import utils.transform_data as backbone

def app(go):
    st.title("Payer Rates")

    facility = st.session_state.get("facility")
    attendance_path = st.session_state.get("attendance_path")

    if not facility or not attendance_path:
        st.error("Missing facility configuration environment parameters.")
        return

    # Ask backbone to build state list elements
    backbone.initialize_payer_rates_state(facility, attendance_path)

    st.subheader("Payer Adjustment Rates")

    for i, row in enumerate(st.session_state.payer_rows):
        col1, col2 = st.columns([4, 2])
        with col1:
            st.text_input(f"Payer {i}", value=row["payer"], disabled=True, key=f"payer_{i}")
        with col2:
            row["adjustment_percent"] = st.number_input(
                "Adjustment %", 
                value=float(row["adjustment_percent"]), 
                step=0.01, 
                key=f"adjustment_{i}"
            )

    st.divider()

    if st.button("Save Payer Rates"):
        try:
            # Deliver array back to backbone for database serialization
            backbone.save_payer_rates_to_db(facility, st.session_state.payer_rows)
            st.success("Payer adjustment profiles updated by Backbone!")
            go("review")
        except Exception as e:
            st.error(f"Save action rejected by backbone process: {e}")