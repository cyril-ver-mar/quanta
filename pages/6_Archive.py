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
from src.utils.config import AppSettings
from src.utils.i18n import t

st.set_page_config(page_title="Quanta · Archive", layout="wide")
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_archive", lang))

st.markdown(
    """
Export a zip on the **Windows** machine after calculations, copy it here, then **Import** on **Mac**
to analyze without Gaussian.
"""
)

svc = ArchiveService()
jobs = JobService().list_jobs()
ids = [j.id for j in jobs if j.id is not None]
selected = st.multiselect("Jobs to export (empty = all on disk)", options=ids, default=ids[:5])

if st.button("Export zip"):
    path = svc.export_jobs(selected or None)
    st.success(f"Wrote {path}")
    st.download_button("Download archive", path.read_bytes(), file_name=path.name)

uploaded = st.file_uploader("Import archive zip", type=["zip"])
if uploaded and st.button("Import"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = Path(tmp.name)
    try:
        imported = svc.import_archive(tmp_path)
        st.success(f"Imported jobs: {imported}")
    except Exception as exc:
        st.error(str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)
