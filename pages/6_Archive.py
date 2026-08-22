"""Archive — export/import portable zip for Mac analysis."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.archive_service import ArchiveService
from src.services.job_service import JobService
from src.ui.components.sidebar import render_sidebar
from src.ui.project_state import get_project, project_compound_ids
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t

st.set_page_config(page_title="Quanta · Archive", layout="wide")
init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_archive", lang))

if get_project() is None:
    st.info(t("need_project", lang))
    st.stop()

st.markdown(t("archive_help_md", lang))

svc = ArchiveService()
jobs = JobService().list_jobs_for_compounds(project_compound_ids())
ids = [j.id for j in jobs if j.id is not None]
selected = st.multiselect(t("archive_jobs_select", lang), options=ids, default=ids[:5])

if st.button(t("archive_export", lang)):
    path = svc.export_jobs(selected or None)
    st.success(t("archive_wrote", lang, path=path))
    st.download_button(t("archive_download", lang), path.read_bytes(), file_name=path.name)

uploaded = st.file_uploader(t("archive_upload", lang), type=["zip"])
if uploaded and st.button(t("import_btn", lang)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = Path(tmp.name)
    try:
        imported = svc.import_archive(tmp_path)
        st.success(t("archive_imported", lang, imported=imported))
    except Exception as exc:
        st.error(str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)
