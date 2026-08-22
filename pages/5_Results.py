"""Results — parse curated XPS / SCF summaries."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.job_service import JobService
from src.services.results_service import ResultsService
from src.ui.components.sidebar import render_sidebar
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import FIXTURES_DIR, job_dir

st.set_page_config(page_title="Quanta · Results", layout="wide")
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_results", lang))

jobs = JobService().list_jobs()
results = ResultsService()

st.subheader("Analyze fixture (melanine)")
if st.button("Curate fixtures/melanine/MELANINE.LOG into a demo job folder"):
    # Create a synthetic job folder #0-style under jobs/demo_melanine via id import
    from src.core.models import Compound, Job, JobStatus
    from src.db.repositories import CompoundRepository, JobRepository
    from src.utils.paths import job_dir as jd
    import shutil

    crepo = CompoundRepository()
    jrepo = JobRepository()
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
    jid = jrepo.add(
        Job(
            id=None,
            compound_id=cid,
            name="melanine_fixture",
            status=JobStatus.COMPLETED,
            route="opt b3lyp/6-31g(d) pop=full",
            nproc=4,
            mem_mb=1500,
        )
    )
    d = jd(jid)
    shutil.copy2(FIXTURES_DIR / "melanine" / "MELANINE.LOG", d / "raw" / "MELANINE.LOG")
    shutil.copy2(FIXTURES_DIR / "melanine" / "melanine.gjf", d / "input" / "melanine.gjf")
    summary = results.curate_job(jid, settings)
    st.success(f"Curated fixture as job #{jid} with {len(summary['core_levels'])} core levels")
    st.session_state.selected_job_id = jid

if not jobs:
    st.info("No jobs in DB yet. Curate the melanine fixture above or run calculations.")
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

    if st.button("Re-curate / analyze log"):
        try:
            summary = results.curate_job(jid, settings)
            st.success(f"Analyzed: {len(summary.get('core_levels', []))} core levels")
        except Exception as exc:
            st.error(str(exc))

    summary = results.load_summary(jid)
    if not summary:
        st.warning("No curated summary yet — click analyze.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("HOMO (eV)", f"{summary.get('homo_ev'):.3f}" if summary.get("homo_ev") is not None else "—")
        m2.metric("LUMO (eV)", f"{summary.get('lumo_ev'):.3f}" if summary.get("lumo_ev") is not None else "—")
        m3.metric("Gap (eV)", f"{summary.get('gap_ev'):.3f}" if summary.get("gap_ev") is not None else "—")
        m4.metric("OPT steps", summary.get("opt_steps"))

        scf = summary.get("scf_energies_ha") or []
        if scf:
            st.subheader("SCF energy history")
            st.line_chart(pd.DataFrame({"SCF_ha": scf}))

        cores = pd.DataFrame(summary.get("core_levels") or [])
        if not cores.empty:
            st.subheader("Core levels (C/N/O)")
            st.dataframe(cores, use_container_width=True)
            csv_path = job_dir(jid) / "curated" / "core_levels.csv"
            if csv_path.exists():
                st.download_button("Download core_levels.csv", csv_path.read_bytes(), file_name="core_levels.csv")

        st.subheader("Simulated XPS (Voigt)")
        for element in ("C", "N", "O"):
            spec = job_dir(jid) / "curated" / f"xps_{element}1s.csv"
            if not spec.exists():
                continue
            df = pd.read_csv(spec)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["binding_ev"], y=df["intensity"], mode="lines", name=f"{element}1s"))
            fig.update_layout(
                title=f"{element}1s",
                xaxis_title="Binding energy (eV)",
                yaxis_title="Intensity (a.u.)",
                xaxis_autorange="reversed",
            )
            st.plotly_chart(fig, use_container_width=True)
