"""Quanta entrypoint — page config, session defaults, home."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.connection import init_db
from src.services import project_service
from src.ui.components.sidebar import render_sidebar
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import ensure_runtime_dirs
from src.utils.secrets import load_secrets

SESSION_DEFAULTS = {
    "settings_loaded": False,
    "selected_job_id": None,
    "selected_compound_id": None,
    "project": None,
    "active_entry_id": None,
}

st.set_page_config(page_title="Quanta", layout="wide", initial_sidebar_state="expanded")

init_session_state()
for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

ensure_runtime_dirs()
load_secrets()  # optional root SECRETS file (GitHub token, etc.)
init_db()
project_service.ensure_legacy_migration()
settings = AppSettings.load()
settings = render_sidebar(settings)

st.title(t("app_title", settings.language))
st.caption(t("app_tagline", settings.language))

st.markdown(t("home_workflow_md", settings.language))
