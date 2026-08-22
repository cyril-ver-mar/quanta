"""Quanta entrypoint — translated navigation (XPS-Deconv style)."""

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
load_secrets()
init_db()
project_service.ensure_legacy_migration()


def _home() -> None:
    settings = AppSettings.load()
    settings = render_sidebar(settings)
    lang = settings.language
    st.title(t("app_title", lang))
    st.caption(t("app_tagline", lang))
    st.markdown(t("home_workflow_md", lang))


# Language for nav titles: prefer session / saved settings
_settings = AppSettings.load()
_lang = st.session_state.get("language") or _settings.language

main = [
    st.Page(_home, title=t("nav_home", _lang), icon="🏠", default=True),
    st.Page("pages/0_Project.py", title=t("nav_project", _lang), icon="📂"),
    st.Page("pages/1_Compounds.py", title=t("nav_compounds", _lang), icon="🧪"),
    st.Page("pages/2_Work_Review.py", title=t("nav_work_review", _lang), icon="🔎"),
]
workflow = [
    st.Page("pages/3_Jobs.py", title=t("nav_jobs", _lang), icon="🧬"),
    st.Page("pages/4_Queue.py", title=t("nav_queue", _lang), icon="⏳"),
    st.Page("pages/5_Results.py", title=t("nav_results", _lang), icon="📈"),
]
data = [
    st.Page("pages/6_Archive.py", title=t("nav_archive", _lang), icon="💾"),
    st.Page("pages/7_Settings.py", title=t("nav_settings", _lang), icon="⚙️"),
]

nav = st.navigation(
    {
        t("nav_group_main", _lang): main,
        t("nav_group_workflow", _lang): workflow,
        t("nav_group_data", _lang): data,
    }
)
nav.run()
