"""Streamlit session bridge for the active Quanta project."""

from __future__ import annotations

import streamlit as st

from src.core.project import QuantaProject


def get_project() -> QuantaProject | None:
    proj = st.session_state.get("project")
    return proj if isinstance(proj, QuantaProject) else None


def set_project(project: QuantaProject | None) -> None:
    st.session_state["project"] = project
    if project is None:
        st.session_state["active_entry_id"] = None
        st.session_state.pop("selected_compound_id", None)
        return
    active = project.get_active()
    st.session_state["active_entry_id"] = project.active_entry_id
    if active and active.compound_id:
        st.session_state["selected_compound_id"] = active.compound_id


def get_active_compound_id() -> int | None:
    project = get_project()
    if project is None:
        return st.session_state.get("selected_compound_id")
    active = project.get_active()
    if active and active.compound_id:
        return active.compound_id
    return st.session_state.get("selected_compound_id")


def project_compound_ids() -> list[int]:
    project = get_project()
    if project is None:
        return []
    return project.compound_ids()
