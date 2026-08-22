"""L5 — ΔSCF workflow step timeline for Jobs / Results pages."""

from __future__ import annotations

import streamlit as st

from src.core.dscf import DscfStep, StepKind, StepStatus, workflow_progress
from src.utils.i18n import t


_STATUS_ICON = {
    StepStatus.WAITING: "⏳",
    StepStatus.QUEUED: "📋",
    StepStatus.RUNNING: "▶️",
    StepStatus.COMPLETED: "✅",
    StepStatus.FAILED: "❌",
}


def _step_title(step: DscfStep, n: int, lang: str) -> str:
    if step.kind == StepKind.OPT:
        return t("step_opt_title", lang)
    if step.kind == StepKind.NEUTRAL_SP:
        return t("step_neutral_title", lang)
    if step.kind == StepKind.COREHOLE_SP:
        label = (
            f"{step.element}{(step.atom_index or 0) + 1}"
            if step.element
            else step.title
        )
        return t("step_corehole_title", lang, n=n, label=label)
    return step.title


def _step_hint(step: DscfStep, lang: str) -> str:
    if step.kind == StepKind.OPT:
        return t("step_opt_hint", lang)
    if step.kind == StepKind.NEUTRAL_SP:
        return t("step_neutral_hint", lang)
    if step.kind == StepKind.COREHOLE_SP:
        return t(
            "step_corehole_hint",
            lang,
            atom=(step.atom_index or 0) + 1,
            element=step.element or "?",
        )
    return step.user_hint


def render_workflow_steps(steps: list[DscfStep], lang: str = "en", expanded: bool = True) -> None:
    """Show numbered steps with status, hints, and energies."""
    if not steps:
        st.info(t("workflow_no_steps", lang))
        return

    prog = workflow_progress(steps)
    st.progress(prog, text=t("workflow_progress", lang).format(
        done=sum(1 for s in steps if s.status == StepStatus.COMPLETED),
        total=len(steps),
        pct=int(prog * 100),
    ))

    for i, step in enumerate(steps, start=1):
        icon = _STATUS_ICON.get(step.status, "•")
        title = _step_title(step, i, lang)
        with st.expander(f"{icon} {title}", expanded=expanded and i <= 3):
            c1, c2 = st.columns([1, 3])
            c1.markdown(f"**{t('workflow_status', lang)}**")
            c1.write(step.status.value)
            if step.energy_ha is not None:
                c1.markdown(f"**{t('workflow_energy', lang)}**")
                c1.write(f"{step.energy_ha:.8f} Ha")
            c2.markdown(f"**{t('workflow_what', lang)}**")
            c2.write(_step_hint(step, lang))
            if step.route:
                c2.markdown(f"**{t('workflow_route', lang)}**")
                c2.code(step.route, language=None)
            if step.gjf_name:
                c2.caption(
                    t("workflow_io_caption", lang, gjf=step.gjf_name, log=step.log_name)
                )
            if step.orbital_index and step.homo_index:
                c2.caption(
                    t(
                        "workflow_alter_caption",
                        lang,
                        orbital=step.orbital_index,
                        homo=step.homo_index,
                    )
                )
            if step.error:
                st.error(step.error)


def render_workflow_overview(lang: str = "en") -> None:
    """Static overview shown before a job exists."""
    st.markdown(t("workflow_overview_md", lang))
