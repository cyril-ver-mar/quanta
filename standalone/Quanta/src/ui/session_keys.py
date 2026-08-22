"""Default Streamlit session keys."""

from __future__ import annotations

import streamlit as st


DEFAULTS: dict = {
    "settings_loaded": False,
    "selected_job_id": None,
    "selected_compound_id": None,
    "project": None,
    "active_entry_id": None,
}


def init_session_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value
