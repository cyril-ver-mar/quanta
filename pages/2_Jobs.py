"""Jobs — create Gaussian OPT/XPS jobs from compounds."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.compound_service import CompoundService
from src.services.job_service import JobService
from src.ui.components.sidebar import render_sidebar
from src.utils.config import AppSettings
from src.utils.i18n import t

st.set_page_config(page_title="Quanta · Jobs", layout="wide")
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_jobs", lang))

compounds = CompoundService().list_compounds()
jobs = JobService()

if not compounds:
    st.warning("Import a compound first.")
else:
    options = {f"#{c.id} {c.name}": c.id for c in compounds}
    label = st.selectbox("Compound", list(options.keys()))
    job_name = st.text_input("Job name", value="")
    st.caption(f"Route: `opt b3lyp/6-31g(d) pop=full …` · nproc={settings.nproc} · mem={settings.mem_mb} MB")
    if st.button("Create job (queued)"):
        jid = jobs.create_job(options[label], settings, name=job_name or None)
        st.success(f"Created job id={jid}")

st.subheader("All jobs")
for job in jobs.list_jobs():
    st.write(
        f"**#{job.id}** `{job.status.value}` — {job.name} "
        f"(compound {job.compound_id}, progress {job.progress:.0%})"
    )
    if job.error:
        st.error(job.error)
