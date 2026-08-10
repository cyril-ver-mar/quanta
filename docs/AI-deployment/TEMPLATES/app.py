"""Application entry — config + session defaults + navigation only."""

from __future__ import annotations

import streamlit as st

# Initialize every key pages will use (adapt to your app)
SESSION_DEFAULTS: dict = {
    "active_project_id": None,
    "ui_language": "en",
}

st.set_page_config(page_title="App", layout="wide")

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.title("Home")
st.caption("Replace with your product name and short tagline.")
st.info("Open pages from the sidebar. Keep business logic in `src/services/`.")
