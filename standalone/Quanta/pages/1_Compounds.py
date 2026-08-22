"""Compounds — upload mol2/pdb/sdf + test molecules."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.models import Compound, JobStatus
from src.core.dscf import StepStatus
from src.db.repositories import CompoundRepository, JobRepository
from src.services.compound_service import CompoundService
from src.services import project_service
from src.services.fixture_service import import_chong_test_molecules
from src.services.job_service import JobService
from src.ui.components.sidebar import render_sidebar
from src.ui.project_state import get_project, project_compound_ids, set_project
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import FIXTURES_DIR, job_dir

init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_compounds", lang))

project = get_project()
if project is None:
    st.info(t("need_project", lang))
    st.stop()

svc = CompoundService()
uploaded = st.file_uploader(t("upload", lang), type=["mol2", "pdb", "sdf", "mol"])
name = st.text_input(t("compound_name", lang), value="")
c1, c2 = st.columns(2)
charge = c1.number_input(t("charge", lang), value=0, step=1)
mult = c2.number_input(t("multiplicity", lang), value=1, min_value=1, step=1)

if uploaded and st.button(t("import_btn", lang)):
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = Path(tmp.name)
    try:
        cid = svc.import_file(
            tmp_path,
            name=name or Path(uploaded.name).stem,
            charge=int(charge),
            multiplicity=int(mult),
        )
        project_service.add_compound_to_project(
            project, cid, label=name or Path(uploaded.name).stem
        )
        set_project(project_service.load_project(project.id))
        st.session_state.selected_compound_id = cid
        st.success(t("compound_imported", lang, id=cid))
    except Exception as exc:
        st.error(str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

st.subheader(t("compounds_test_mols", lang))
st.caption(t("results_chong_hint", lang))
col_a, col_b = st.columns(2)
if col_a.button(t("results_chong_btn", lang)):
    try:
        imported = import_chong_test_molecules(project)
        set_project(project_service.load_project(project.id))
        names = ", ".join(f"{n} (#{cid})" for n, cid in imported)
        st.success(t("results_chong_ok", lang, names=names))
        st.rerun()
    except Exception as exc:
        st.error(str(exc))

if col_b.button(t("results_fixture_btn", lang)):
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
    jid = js.create_job(
        cid,
        settings,
        name="melanine_fixture",
        project_name=project.name,
    )
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
    project_service.add_compound_to_project(project, cid, label="melanine")
    set_project(project_service.load_project(project.id))
    st.session_state.selected_job_id = jid
    st.info(t("results_fixture_note", lang).format(job_id=jid))

st.subheader(t("compound_library", lang))
rows = svc.list_compounds_for_project(project_compound_ids())
if not rows:
    st.info(t("compound_empty", lang))
else:
    for comp in rows:
        with st.expander(f"#{comp.id} {comp.name} ({comp.formula})"):
            st.write(
                {
                    t("field_format", lang): comp.source_format,
                    t("atoms", lang): comp.n_atoms,
                    t("charge", lang): comp.charge,
                    t("multiplicity", lang): comp.multiplicity,
                    t("path_label", lang): comp.source_path,
                    t("meta_label", lang): comp.meta_json,
                }
            )
            nc = st.number_input(t("charge", lang), value=comp.charge, key=f"ch_{comp.id}")
            nm = st.number_input(
                t("multiplicity", lang),
                value=comp.multiplicity,
                min_value=1,
                key=f"mu_{comp.id}",
            )
            if st.button(t("save", lang), key=f"save_{comp.id}"):
                svc.update_charge_mult(int(comp.id), int(nc), int(nm))
                st.rerun()
            if st.button(t("compound_goto_review", lang), key=f"review_{comp.id}"):
                st.session_state.selected_compound_id = comp.id
                st.switch_page("pages/2_Work_Review.py")
