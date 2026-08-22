"""Queue — run / pause / delete pending / restart."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.dscf import StepStatus
from src.services.gaussian_runner import GaussianRunner, gaussian_available
from src.services.job_service import JobService
from src.services.gaussian_parser import parse_gaussian_log
from src.ui.components.log_viewer import list_job_logs, render_gaussian_log_viewer
from src.ui.components.sidebar import render_sidebar
from src.ui.components.workflow_steps import render_workflow_steps
from src.ui.project_state import get_project, project_compound_ids
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import job_dir

init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_queue", lang))
st.caption(t("queue_dscf_caption", lang))

if get_project() is None:
    st.info(t("need_project", lang))
    st.stop()

pids = project_compound_ids()

svc = JobService()
can_run = gaussian_available(settings)

c1, c2, c3, c4 = st.columns(4)
if c1.button(t("queue_run_next", lang), disabled=not can_run):
    with st.spinner(t("queue_running", lang)):
        jid = GaussianRunner().run_next(settings)
    if jid:
        st.success(t("queue_finished", lang, job_id=jid))
    else:
        st.info(t("queue_nothing", lang))
if c2.button(t("queue_pause", lang)):
    svc.pause_queue()
    st.rerun()
if c3.button(t("queue_resume", lang)):
    svc.resume_queue()
    st.rerun()

jobs = svc.list_jobs_for_compounds(pids)
if not jobs:
    st.info(t("workflow_no_jobs", lang))
else:
    df = pd.DataFrame(
        [
            {
                t("col_id", lang): j.id,
                t("col_name", lang): j.name,
                t("col_status", lang): j.status.value,
                t("col_current_step", lang): (j.meta_json or {}).get("current_step"),
                t("col_progress", lang): f"{j.progress:.0%}",
                t("col_eta", lang): (j.meta_json or {}).get("eta_s"),
                t("col_error", lang): j.error,
            }
            for j in jobs
        ]
    )
    st.dataframe(df, use_container_width=True)

    selected = st.number_input(t("job_id", lang), min_value=1, step=1, value=int(jobs[0].id or 1))
    job = next((j for j in jobs if j.id == int(selected)), None)
    steps = svc.get_steps(int(selected))
    if steps:
        st.subheader(t("workflow_title", lang))
        render_workflow_steps(steps, lang=lang, expanded=True)

    a1, a2, a3 = st.columns(3)
    if a1.button(t("queue_delete_pending", lang)):
        try:
            svc.delete_pending(int(selected))
            st.success(t("queue_deleted", lang))
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if a2.button(t("queue_restart", lang)):
        try:
            svc.restart_failed(int(selected), settings)
            st.success(t("queue_requeued", lang))
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if a3.button(t("queue_refresh", lang)):
        st.rerun()

    jdir = job_dir(int(selected))
    gauss_cwd = (job.meta_json or {}).get("gaussian_cwd") if job else None
    logs = list_job_logs(jdir, gaussian_cwd=gauss_cwd)

    preferred = None
    if steps:
        failed = [s for s in steps if s.status == StepStatus.FAILED and s.log_name]
        running = [s for s in steps if s.status == StepStatus.RUNNING and s.log_name]
        pick = (failed or running or [s for s in reversed(steps) if s.log_name])
        if pick:
            candidate = jdir / "raw" / pick[0].log_name
            if candidate.exists():
                preferred = candidate

    if preferred is None and logs:
        preferred = logs[0]

    job_error = ""
    if job and job.error:
        job_error = job.error
    elif steps:
        for s in steps:
            if s.error:
                job_error = s.error
                break

    # Compact SCF chart when available
    if preferred and preferred.exists():
        parsed = parse_gaussian_log(preferred)
        if parsed.scf_energies_ha:
            st.line_chart(pd.DataFrame({"SCF_ha": parsed.scf_energies_ha}))

    render_gaussian_log_viewer(
        logs,
        lang,
        preferred=preferred,
        job_error=job_error,
    )
