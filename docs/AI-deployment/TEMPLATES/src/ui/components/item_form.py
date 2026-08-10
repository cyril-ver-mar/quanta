"""L5 — thin Streamlit component example."""

from __future__ import annotations

import streamlit as st

from src.services.item_service import ItemService


def render_item_form() -> None:
    name = st.text_input("Name", key="item_name")
    if st.button("Create") and name.strip():
        item = ItemService().create(name)
        st.success(f"Created {item.name}")
