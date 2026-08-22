"""Results — ΔSCF XPS binding energies and simulated spectra."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.models import Compound, JobStatus
from src.core.dscf import StepStatus
from src.db.repositories import CompoundRepository, JobRepository
from src.services.job_service import JobService
from src.services.results_service import ResultsService
from src.services import project_service
from src.ui.components.sidebar import render_sidebar
from src.ui.components.workflow_steps import render_workflow_steps
from src.ui.project_state import get_project, project_compound_ids, set_project
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import FIXTURES_DIR, job_dir

st.set_page_config(page_title="Quanta · Results", layout="wide")
init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_results", lang))
st.caption(t("results_dscf_caption", lang))

if get_project() is None:
    st.info(t("need_project", lang))
    st.stop()

pids = project_compound_ids()
jobs = JobService().list_jobs_for_compounds(pids)
results = ResultsService()

st.subheader(t("results_fixture", lang))
if st.button(t("results_fixture_btn", lang)):
    import shutil

    crepo = CompoundRepository()
    jrepo = JobRepository()
    js = JobService()

    cid = crepo.add(
        Compound(
            id=None,
            name="melanine",
            source_format="gjf",
            source_path=str(FIXTURES_DIR / "melanine" / "melanine.gjf"),
            charge=0,
            multiplicity=1,
            formula="C3H6N6",
            n_atoms=15,
            meta_json={"elements": {"C": 3, "N": 6, "H": 6}},
        )
    )
    jid = js.create_job(cid, settings, name="melanine_fixture")
    d = job_dir(jid)
    shutil.copy2(FIXTURES_DIR / "melanine" / "MELANINE.LOG", d / "raw" / f"job_{jid}_01_opt.log")
    shutil.copy2(FIXTURES_DIR / "melanine" / "melanine.gjf", d / "input" / "melanine.gjf")
    steps = js.get_steps(jid)
    for step in steps:
        if step.key == "opt":
            step.status = StepStatus.COMPLETED
            step.energy_ha = -493.0
    js.save_steps(jid, steps)
    job = jrepo.get(jid)
    if job:
        job.status = JobStatus.QUEUED
        jrepo.update(job)
    st.info(t("results_fixture_note", lang).format(job_id=jid))
    st.session_state.selected_job_id = jid
    proj = get_project()
    if proj is not None:
        project_service.add_compound_to_project(proj, cid, label="melanine")
        set_project(project_service.load_project(proj.id))

if not jobs:
    st.info(t("workflow_no_jobs", lang))
else:
    labels = {f"#{j.id} {j.name} [{j.status.value}]": j.id for j in jobs}
    default_ix = 0
    if st.session_state.get("selected_job_id") in labels.values():
        keys = list(labels.keys())
        for i, k in enumerate(keys):
            if labels[k] == st.session_state.selected_job_id:
                default_ix = i
                break
    choice = st.selectbox("Job", list(labels.keys()), index=default_ix)
    jid = labels[choice]

    job_svc = JobService()
    steps = job_svc.get_steps(jid)
    if steps:
        st.subheader(t("workflow_title", lang))
        render_workflow_steps(steps, lang=lang, expanded=False)

    if st.button(t("results_recurate", lang)):
        try:
            summary = results.curate_job(jid, settings)
            st.success(t("results_curated", lang).format(n=len(summary.get("core_levels", []))))
        except Exception as exc:
            st.error(str(exc))

    summary = results.load_summary(jid)
    if not summary:
        st.warning(t("results_no_summary", lang))
    else:
        if summary.get("protocol") == "dscf":
            e0 = summary.get("e0_ha")
            if e0 is not None:
                st.metric("E₀ (Ha)", f"{e0:.8f}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("HOMO (eV)", f"{summary.get('homo_ev'):.3f}" if summary.get("homo_ev") is not None else "—")
        m2.metric("LUMO (eV)", f"{summary.get('lumo_ev'):.3f}" if summary.get("lumo_ev") is not None else "—")
        m3.metric("Gap (eV)", f"{summary.get('gap_ev'):.3f}" if summary.get("gap_ev") is not None else "—")
        m4.metric("Core-hole jobs", summary.get("n_corehole_jobs", "—"))

        cores = pd.DataFrame(summary.get("core_levels") or [])
        if not cores.empty:
            st.subheader(t("results_core_levels", lang))
            st.dataframe(cores, use_container_width=True)
            csv_path = job_dir(jid) / "curated" / "core_levels.csv"
            if csv_path.exists():
                st.download_button(
                    "core_levels.csv",
                    csv_path.read_bytes(),
                    file_name="core_levels.csv",
                )

        st.subheader(t("results_spectra", lang))
        for element in ("C", "N", "O"):
            spec = job_dir(jid) / "curated" / f"xps_{element}1s.csv"
            if not spec.exists():
                continue
            df = pd.read_csv(spec)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["binding_ev"], y=df["intensity"], mode="lines", name=f"{element}1s"))
            fig.update_layout(
                title=f"{element}1s (ΔSCF + Voigt)",
                xaxis_title="Binding energy (eV)",
                yaxis_title="Intensity (a.u.)",
                xaxis_autorange="reversed",
            )
            st.plotly_chart(fig, use_container_width=True)
