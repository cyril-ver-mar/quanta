"""Results — ΔSCF XPS binding energies and simulated spectra."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.repositories import CompoundRepository
from src.services.job_service import JobService
from src.services.results_service import ResultsService
from src.ui.components.sidebar import render_sidebar
from src.ui.components.log_viewer import list_job_logs, render_gaussian_log_viewer
from src.ui.components.spectrum_panel import render_simulated_spectra
from src.ui.components.workflow_steps import render_workflow_steps
from src.ui.project_state import get_project, project_compound_ids
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import job_dir

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
compounds = CompoundRepository()

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
    choice = st.selectbox(t("results_job_select", lang), list(labels.keys()), index=default_ix)
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
                st.metric(t("results_e0", lang), f"{e0:.8f}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            t("results_homo", lang),
            f"{summary.get('homo_ev'):.3f}" if summary.get("homo_ev") is not None else "—",
        )
        m2.metric(
            t("results_lumo", lang),
            f"{summary.get('lumo_ev'):.3f}" if summary.get("lumo_ev") is not None else "—",
        )
        m3.metric(
            t("results_gap", lang),
            f"{summary.get('gap_ev'):.3f}" if summary.get("gap_ev") is not None else "—",
        )
        m4.metric(t("results_n_corehole", lang), summary.get("n_corehole_jobs", "—"))

        cores = pd.DataFrame(summary.get("core_levels") or [])
        if not cores.empty:
            st.subheader(t("results_core_levels", lang))
            st.dataframe(cores, use_container_width=True)
            csv_path = job_dir(jid) / "curated" / "core_levels.csv"
            if csv_path.exists():
                st.download_button(
                    t("results_dl_core_csv", lang),
                    csv_path.read_bytes(),
                    file_name="core_levels.csv",
                )
            raw_bes = [
                float(x)
                for x in cores["be_raw_ev"].tolist()
                if x is not None and str(x) != "nan"
            ]
            if raw_bes and max(raw_bes) < 50.0:
                st.warning(t("results_be_looks_valence", lang))
        else:
            skipped = summary.get("curation_skipped") or []
            st.warning(t("results_no_core_levels", lang))
            if skipped:
                st.caption("; ".join(str(s) for s in skipped[:12]))

        job_obj = job_svc.get(jid)
        compound_name = None
        if job_obj is not None:
            comp = compounds.get(job_obj.compound_id)
            if comp is not None:
                compound_name = comp.name

        render_simulated_spectra(
            summary,
            lang=lang,
            compound_name=compound_name,
            default_fwhm=float(settings.xps_fwhm_ev),
        )

    job_obj = job_svc.get(jid)
    gauss_cwd = (job_obj.meta_json or {}).get("gaussian_cwd") if job_obj else None
    logs = list_job_logs(job_dir(jid), gaussian_cwd=gauss_cwd)
    err = ""
    if job_obj and job_obj.error:
        err = job_obj.error
    elif steps:
        for s in steps:
            if s.error:
                err = s.error
                break
    render_gaussian_log_viewer(logs, lang, job_error=err)
