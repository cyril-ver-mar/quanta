"""Work review — 3D structure preview before calculations."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.review_service import ReviewService
from src.ui.components.mol_viewer import render_molecule_3d
from src.ui.components.sidebar import render_sidebar
from src.ui.project_state import get_project, project_compound_ids
from src.ui.session_keys import init_session_state
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.services.compound_service import CompoundService
from src.services.job_service import JobService

init_session_state()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_work_review", lang))
st.caption(t("review_caption", lang))

if get_project() is None:
    st.info(t("need_project", lang))
    st.stop()

compound_ids = set(project_compound_ids())
compounds = [c for c in CompoundService().list_compounds() if c.id in compound_ids]
if not compounds:
    st.info(t("review_no_compounds", lang))
    st.stop()

labels = {f"#{c.id} · {c.name} ({c.formula})": c.id for c in compounds}
default_ix = 0
if st.session_state.get("selected_compound_id") in labels.values():
    for i, label in enumerate(labels):
        if labels[label] == st.session_state.selected_compound_id:
            default_ix = i
            break

choice = st.selectbox(t("review_select", lang), list(labels.keys()), index=default_ix)
compound_id = labels[choice]
st.session_state.selected_compound_id = compound_id

style = st.radio(
    t("review_style", lang),
    options=["stick", "ballstick", "sphere", "line"],
    horizontal=True,
    format_func=lambda s: t("review_style_ballstick", lang) if s == "ballstick" else s,
)

try:
    bundle = ReviewService().load(compound_id)
except Exception as exc:
    st.error(str(exc))
    st.stop()

comp = bundle.compound
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric(t("atoms", lang), comp.n_atoms)
m2.metric(t("charge", lang), comp.charge)
m3.metric(t("multiplicity", lang), comp.multiplicity)
m4.metric(t("formula", lang), comp.formula)
m5.metric(t("field_format", lang), comp.source_format.upper())

elements = (comp.meta_json or {}).get("elements") or {}
if elements:
    el_list = ", ".join(f"{k}×{v}" for k, v in sorted(elements.items()))
    st.caption(t("review_elements", lang, list=el_list))

st.subheader(t("review_3d", lang))
render_molecule_3d(bundle.mol_block, fmt="mol", style=style)

with st.expander(t("review_atoms", lang), expanded=False):
    st.dataframe(pd.DataFrame(bundle.atoms), use_container_width=True, hide_index=True)

st.subheader(t("review_jobs", lang))
if not bundle.jobs:
    st.info(t("review_no_jobs", lang))
else:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    t("col_id", lang): j.id,
                    t("col_name", lang): j.name,
                    t("col_status", lang): j.status.value,
                    t("col_progress", lang): j.progress,
                    t("col_route", lang): j.route,
                }
                for j in bundle.jobs
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander(t("review_gjf_preview", lang)):
    try:
        gjf = CompoundService().build_gjf_text(
            comp,
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
            chk_name=f"preview_{comp.id}.chk",
        )
        st.code(gjf, language="text")
    except Exception as exc:
        st.error(str(exc))

if st.button(t("review_create_job", lang)):
    proj = get_project()
    jid = JobService().create_job(
        compound_id,
        settings,
        project_name=proj.name if proj else None,
    )
    st.success(t("review_job_queued", lang, id=jid))
    st.session_state.selected_job_id = jid
    st.rerun()
