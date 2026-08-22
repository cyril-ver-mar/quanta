"""Jobs — create ΔSCF XPS workflows from compounds."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.dscf import DscfSettings, opt_route
from src.services.compound_service import CompoundService
from src.services.job_service import JobService
from src.ui.components.sidebar import render_sidebar
from src.ui.components.workflow_steps import render_workflow_overview, render_workflow_steps
from src.ui.project_state import get_project, project_compound_ids
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t

init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_jobs", lang))

if get_project() is None:
    st.info(t("need_project", lang))
    st.stop()

pids = project_compound_ids()

dscf = DscfSettings(
    functional=settings.dscf_functional,
    basis=settings.dscf_basis,
    fwhm_ev=settings.xps_fwhm_ev,
    c1s_ref_ev=settings.xps_c1s_ref_ev,
    apply_c1s_shift=settings.dscf_apply_c1s_shift,
)

st.subheader(t("workflow_title", lang))
render_workflow_overview(lang)

st.divider()
st.subheader(t("workflow_create", lang))

compounds = CompoundService().list_compounds_for_project(pids)
jobs = JobService()

if not compounds:
    st.warning(t("workflow_import_first", lang))
else:
    options = {f"#{c.id} {c.name} ({c.formula})": c.id for c in compounds}
    label = st.selectbox(t("workflow_compound", lang), list(options.keys()))
    compound = compounds[[c.id for c in compounds].index(options[label])]
    job_name = st.text_input(t("workflow_job_name", lang), value="")

    elements = (compound.meta_json or {}).get("elements") or {}
    n_xps = sum(elements.get(el, 0) for el in ("C", "N", "O"))
    st.info(
        t("workflow_job_summary", lang).format(
            n_xps=n_xps,
            n_steps=2 + n_xps,
            functional=dscf.functional,
            basis=dscf.basis,
        )
    )
    st.caption(
        t(
            "workflow_route_caption",
            lang,
            route=opt_route(dscf),
            nproc=settings.nproc,
            mem=settings.mem_mb,
        )
    )

    if st.button(t("workflow_create_btn", lang), type="primary"):
        proj = get_project()
        jid = jobs.create_job(
            options[label],
            settings,
            name=job_name or None,
            project_name=proj.name if proj else None,
        )
        st.session_state.selected_job_id = jid
        st.success(t("workflow_created", lang).format(job_id=jid))
        st.rerun()

st.divider()
st.subheader(t("workflow_existing", lang))

all_jobs = jobs.list_jobs_for_compounds(pids)
if not all_jobs:
    st.caption(t("workflow_no_jobs", lang))
else:
    for job in all_jobs:
        steps = jobs.get_steps(job.id or 0)
        header = f"**#{job.id}** `{job.status.value}` — {job.name}"
        st.markdown(header)
        if steps:
            render_workflow_steps(steps, lang=lang, expanded=(job.id == st.session_state.get("selected_job_id")))
        if job.error:
            st.error(job.error)
        st.divider()
