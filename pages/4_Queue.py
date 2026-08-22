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
from src.ui.components.workflow_steps import render_workflow_steps
from src.ui.project_state import get_project, project_compound_ids
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import job_dir
from src.core.dscf import StepStatus
from src.services.gaussian_parser import parse_gaussian_log

st.set_page_config(page_title="Quanta · Queue", layout="wide")
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
            svc.restart_failed(int(selected))
            st.success(t("queue_requeued", lang))
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if a3.button(t("queue_refresh", lang)):
        st.rerun()

    jdir = job_dir(int(selected))
    step_logs = [s.log_name for s in steps if s.status == StepStatus.RUNNING] if steps else []
    log_name = step_logs[0] if step_logs else None
    log_path = jdir / "raw" / log_name if log_name else None
    if log_path is None or not log_path.exists():
        candidates = list((jdir / "raw").glob("*.log")) + list((jdir / "raw").glob("*.LOG"))
        log_path = max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None
    if log_path and log_path.exists():
        parsed = parse_gaussian_log(log_path)
        st.subheader(t("queue_live_log", lang))
        st.caption(str(log_path.name))
        st.write(
            {
                t("monitor_opt_steps", lang): parsed.opt_steps,
                t("monitor_progress", lang): parsed.progress_estimate,
                t("monitor_scf_points", lang): len(parsed.scf_energies_ha),
                t("monitor_normal_term", lang): parsed.normal_termination,
            }
        )
        if parsed.scf_energies_ha:
            st.line_chart(pd.DataFrame({"SCF_ha": parsed.scf_energies_ha}))
