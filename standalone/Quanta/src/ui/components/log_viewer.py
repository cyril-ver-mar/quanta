"""L5 — Gaussian log viewer for Queue / Results diagnostics."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.services.gaussian_parser import parse_gaussian_log, read_log_text, tail_lines
from src.utils.i18n import t


def list_job_logs(job_dir_path: Path, *, gaussian_cwd: str | None = None) -> list[Path]:
    """Collect .log / .out files for a job (app raw/ + optional Gaussian cwd)."""
    found: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen or not path.is_file():
            return
        seen.add(key)
        found.append(path)

    raw = job_dir_path / "raw"
    if raw.is_dir():
        for pat in ("*.log", "*.LOG", "*.out", "*.OUT"):
            for p in sorted(raw.glob(pat), key=lambda x: x.stat().st_mtime, reverse=True):
                _add(p)

    if gaussian_cwd:
        cwd = Path(gaussian_cwd)
        if cwd.is_dir():
            for pat in ("*.log", "*.LOG", "*.out", "*.OUT", "*.stdout.txt"):
                for p in sorted(cwd.glob(pat), key=lambda x: x.stat().st_mtime, reverse=True):
                    _add(p)

    return found


def render_gaussian_log_viewer(
    logs: list[Path],
    lang: str,
    *,
    preferred: Path | None = None,
    job_error: str = "",
) -> None:
    """Show error summary + selectable Gaussian log text."""
    st.subheader(t("log_viewer_title", lang))

    if job_error:
        st.error(job_error)

    if not logs:
        st.info(t("log_viewer_empty", lang))
        return

    labels = {f"{p.parent.name}/{p.name}" if p.parent.name else p.name: p for p in logs}
    # Prefer failed / preferred file in the select default
    keys = list(labels.keys())
    default_ix = 0
    if preferred is not None:
        for i, p in enumerate(logs):
            try:
                if p.resolve() == preferred.resolve():
                    default_ix = i
                    break
            except OSError:
                if p == preferred:
                    default_ix = i
                    break

    choice = st.selectbox(
        t("log_viewer_select", lang),
        keys,
        index=min(default_ix, len(keys) - 1),
        key=f"_log_viewer_select_{path_key_seed(logs)}",
    )
    path = labels[choice]
    text = read_log_text(path)
    parsed = parse_gaussian_log(path)

    c1, c2, c3 = st.columns(3)
    c1.metric(t("monitor_normal_term", lang), "yes" if parsed.normal_termination else "no")
    c2.metric(t("monitor_scf_points", lang), len(parsed.scf_energies_ha))
    c3.metric(t("monitor_opt_steps", lang), parsed.opt_steps)

    if parsed.raw_errors:
        st.warning(t("log_viewer_errors_found", lang))
        for snippet in parsed.raw_errors:
            st.code(snippet, language="text")
    elif not parsed.normal_termination:
        st.warning(t("log_viewer_incomplete", lang))

    st.caption(str(path))
    show_full = st.checkbox(
        t("log_viewer_show_full", lang),
        value=bool(parsed.raw_errors),
        key=f"_log_full_{path.name}",
    )
    body = text if show_full else tail_lines(text, 120)
    if not show_full:
        st.caption(t("log_viewer_tail_hint", lang, n=120))
    st.text_area(
        t("log_viewer_body", lang),
        value=body,
        height=420,
        key=f"_log_viewer_body_{path.name}_{int(show_full)}",
    )
    st.download_button(
        t("log_viewer_download", lang),
        data=text,
        file_name=path.name,
        mime="text/plain",
        key=f"_log_viewer_dl_{path.name}",
    )


def path_key_seed(logs: list[Path]) -> str:
    return str(abs(hash(tuple(str(p) for p in logs))) % 10_000_000)