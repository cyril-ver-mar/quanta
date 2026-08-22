"""Queue — run / pause / delete pending / restart."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.models import JobStatus
from src.services.gaussian_runner import GaussianRunner, gaussian_available
from src.services.job_service import JobService
from src.ui.components.sidebar import render_sidebar
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import job_dir
from src.services.gaussian_parser import parse_gaussian_log

st.set_page_config(page_title="Quanta · Queue", layout="wide")
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_queue", lang))

svc = JobService()
can_run = gaussian_available(settings)

c1, c2, c3, c4 = st.columns(4)
if c1.button("Run next job", disabled=not can_run):
    with st.spinner("Running Gaussian…"):
        jid = GaussianRunner().run_next(settings)
    if jid:
        st.success(f"Finished processing job {jid}")
    else:
        st.info("No queued job or Gaussian unavailable")
if c2.button("Pause remaining queue"):
    svc.pause_queue()
    st.rerun()
if c3.button("Resume paused"):
    svc.resume_queue()
    st.rerun()

jobs = svc.list_jobs()
if not jobs:
    st.info("No jobs.")
else:
    df = pd.DataFrame(
        [
            {
                "id": j.id,
                "name": j.name,
                "status": j.status.value,
                "progress": j.progress,
                "eta_s": (j.meta_json or {}).get("eta_s"),
                "opt_steps": (j.meta_json or {}).get("opt_steps"),
                "error": j.error,
            }
            for j in jobs
        ]
    )
    st.dataframe(df, use_container_width=True)

    selected = st.number_input("Job id", min_value=1, step=1, value=int(jobs[0].id or 1))
    a1, a2, a3 = st.columns(3)
    if a1.button("Delete pending"):
        try:
            svc.delete_pending(int(selected))
            st.success("Deleted")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if a2.button("Re-queue / restart"):
        try:
            svc.restart_failed(int(selected))
            st.success("Re-queued")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if a3.button("Refresh monitor"):
        st.rerun()

    jdir = job_dir(int(selected))
    logs = list((jdir / "raw").glob("*.log")) + list((jdir / "raw").glob("*.LOG"))
    if logs:
        parsed = parse_gaussian_log(logs[0])
        st.subheader("Live / last log status")
        st.write(
            {
                "opt_steps": parsed.opt_steps,
                "progress": parsed.progress_estimate,
                "scf_points": len(parsed.scf_energies_ha),
                "normal_termination": parsed.normal_termination,
            }
        )
        if parsed.scf_energies_ha:
            st.line_chart(pd.DataFrame({"SCF_ha": parsed.scf_energies_ha}))
