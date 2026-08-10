"""Example multi-page file — keep thin; call UI components / services."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Home", layout="wide")
st.title("Home")
st.write("Wire this page to `src/ui/components/` as the app grows.")
