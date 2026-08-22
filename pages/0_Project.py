"""Project — create/load workspace and manage compound entries."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.compound_service import CompoundService
from src.services.job_service import JobService
from src.services import project_service
from src.ui.components.sidebar import render_sidebar
from src.ui.project_state import get_project, project_compound_ids, set_project
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t

st.set_page_config(page_title="Quanta · Project", layout="wide")
init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language

st.title(t("nav_project", lang))
st.caption(t("project_page_caption", lang))

project_service.ensure_legacy_migration()

st.subheader(t("project_section", lang))
rows = project_service.list_projects()
c1, c2 = st.columns(2)
with c1:
    new_name = st.text_input(t("new_project_name", lang), value=t("project_default_name", lang))
    if st.button(t("create_project", lang), type="primary"):
        proj = project_service.create_project(new_name)
        set_project(proj)
        st.success(t("created_project", lang, name=proj.name))
        st.rerun()
with c2:
    if rows:
        labels = {
            r["id"]: t(
                "project_list_item",
                lang,
                name=r["name"],
                n=r["n_entries"],
                updated=r["updated_at"][:19],
            )
            for r in rows
        }
        pid = st.selectbox(
            t("load_existing", lang),
            options=list(labels.keys()),
            format_func=lambda i: labels[i],
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button(t("load_project", lang)):
                set_project(project_service.load_project(pid))
                st.success(t("project_loaded", lang))
                st.rerun()
        with b2:
            if st.button(t("delete_project", lang)):
                project_service.delete_project(pid)
                if get_project() and get_project().id == pid:
                    set_project(None)
                st.warning(t("deleted_ok", lang))
                st.rerun()
    else:
        st.caption(t("no_projects", lang))

project = get_project()
if project is None:
    st.info(t("need_project", lang))
    st.stop()

st.success(
    t("active_project", lang, name=project.name, id=project.id, n=len(project.entries))
)
notes = st.text_area(t("project_notes", lang), value=project.notes)
if st.button(t("save_notes", lang)):
    project.notes = notes
    project_service.save_project(project)
    st.toast(t("saved_ok", lang))

st.divider()
st.subheader(t("project_add_compounds", lang))
uploads = st.file_uploader(
    t("upload", lang),
    type=["mol2", "pdb", "sdf", "mol"],
    accept_multiple_files=True,
)
c1, c2 = st.columns(2)
charge = c1.number_input(t("charge", lang), value=0, step=1, key="proj_charge")
mult = c2.number_input(t("multiplicity", lang), value=1, min_value=1, step=1, key="proj_mult")
if uploads and st.button(t("project_import_btn", lang)):
    svc = CompoundService()
    added = 0
    errors: list[str] = []
    for uploaded in uploads:
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = Path(tmp.name)
        try:
            cid = svc.import_file(
                tmp_path,
                name=Path(uploaded.name).stem,
                charge=int(charge),
                multiplicity=int(mult),
            )
            project_service.add_compound_to_project(
                project, cid, label=Path(uploaded.name).stem
            )
            added += 1
        except Exception as exc:
            errors.append(f"{uploaded.name}: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)
    set_project(project_service.load_project(project.id))
    st.success(t("project_added_compounds", lang, n=added))
    for err in errors:
        st.error(err)
    st.rerun()

project = get_project()
assert project is not None

st.subheader(t("project_entries", lang))
if not project.entries:
    st.info(t("project_no_entries", lang))
else:
    job_svc = JobService()
    compound_svc = CompoundService()
    for entry in project.entries:
        comp = compound_svc.get(entry.compound_id)
        n_jobs = len(job_svc.list_jobs_for_compounds([entry.compound_id]))
        label = entry.label or (comp.name if comp else f"#{entry.compound_id}")
        formula = comp.formula if comp else "—"
        with st.expander(
            t(
                "project_entry_jobs",
                lang,
                label=label,
                formula=formula,
                n=n_jobs,
            )
        ):
            st.write(t("project_entry_id", lang, id=entry.id, compound_id=entry.compound_id))
            if comp:
                st.write(
                    {
                        t("charge", lang): comp.charge,
                        t("multiplicity", lang): comp.multiplicity,
                        t("atoms", lang): comp.n_atoms,
                    }
                )
            if st.button(t("project_set_active", lang), key=f"active_{entry.id}"):
                project_service.set_active_entry(project, entry.id)
                set_project(project_service.load_project(project.id))
                st.rerun()
            if st.button(t("project_remove_entry", lang), key=f"rm_{entry.id}"):
                project_service.remove_entry(project, entry.id)
                set_project(project_service.load_project(project.id))
                st.rerun()

active = project.get_active()
if active:
    st.caption(t("project_active_entry", lang, label=active.label, id=active.id))

st.divider()
ids = project_compound_ids()
st.metric(t("project_n_compounds", lang), len(ids))
st.metric(t("project_n_jobs", lang), len(JobService().list_jobs_for_compounds(ids)))
