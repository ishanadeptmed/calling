import streamlit as st

st.set_page_config(page_title="Workflow App", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "login"

def go(page):
    st.session_state.page = page
    st.rerun()

# ROUTING
if st.session_state.page == "login":
    import pages.login as p
    p.app(go)

elif st.session_state.page == "facility":
    import pages.facility as p
    p.app(go)

elif st.session_state.page == "upload":
    import pages.upload as p
    p.app(go)

#when we activate below mentioned snippet we go pages/upload.py and set go to columns replacing rates. 
# elif st.session_state.page == "columns":
#     import pages.columns as p
#     p.app(go)

elif st.session_state.page == "rates":
    import pages.rates as p
    p.app(go)

elif st.session_state.page == "payer_rates":
    import pages.payer_rates as p
    p.app(go)

elif st.session_state.page == "review":
    import pages.review_download as p
    p.app(go)