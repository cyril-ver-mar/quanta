"""Compounds — upload mol2/pdb/sdf."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.compound_service import CompoundService
from src.services import project_service
from src.ui.components.sidebar import render_sidebar
from src.ui.project_state import get_project, project_compound_ids, set_project
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t

st.set_page_config(page_title="Quanta · Compounds", layout="wide")
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
name = st.text_input("Name", value="")
c1, c2 = st.columns(2)
charge = c1.number_input(t("charge", lang), value=0, step=1)
mult = c2.number_input(t("multiplicity", lang), value=1, min_value=1, step=1)

if uploaded and st.button("Import"):
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = Path(tmp.name)
    try:
        cid = svc.import_file(tmp_path, name=name or Path(uploaded.name).stem, charge=int(charge), multiplicity=int(mult))
        project_service.add_compound_to_project(project, cid, label=name or Path(uploaded.name).stem)
        set_project(project_service.load_project(project.id))
        st.session_state.selected_compound_id = cid
        st.success(f"Imported compound id={cid}")
    except Exception as exc:
        st.error(str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

st.subheader("Library")
rows = svc.list_compounds_for_project(project_compound_ids())
if not rows:
    st.info("No compounds yet.")
else:
    for comp in rows:
        with st.expander(f"#{comp.id} {comp.name} ({comp.formula})"):
            st.write(
                {
                    "format": comp.source_format,
                    "atoms": comp.n_atoms,
                    "charge": comp.charge,
                    "multiplicity": comp.multiplicity,
                    "path": comp.source_path,
                    "meta": comp.meta_json,
                }
            )
            nc = st.number_input(f"charge_{comp.id}", value=comp.charge, key=f"ch_{comp.id}")
            nm = st.number_input(f"mult_{comp.id}", value=comp.multiplicity, min_value=1, key=f"mu_{comp.id}")
            if st.button(t("save", lang), key=f"save_{comp.id}"):
                svc.update_charge_mult(int(comp.id), int(nc), int(nm))
                st.rerun()
            if st.button("3D review →", key=f"review_{comp.id}"):
                st.session_state.selected_compound_id = comp.id
                st.switch_page("pages/2_Work_Review.py")
