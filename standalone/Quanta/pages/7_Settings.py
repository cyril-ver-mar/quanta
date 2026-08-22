"""Settings — paths, resources, ΔSCF XPS options."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.components.sidebar import render_sidebar
from src.ui.components.update_banner import render_update_settings
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.secrets import clear_secrets_cache, load_secrets, secrets_status
from src.utils.version import version_label

load_secrets()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_settings", lang))
st.caption(version_label())

st.subheader(t("settings_gaussian", lang))
settings.gaussian_exe = st.text_input(t("settings_gaussian_exe", lang), value=settings.gaussian_exe)
st.caption(t("settings_gaussian_cli_hint", lang))
settings.work_dir = st.text_input(t("settings_work_dir", lang), value=settings.work_dir)
st.caption(t("settings_work_dir_hint", lang))
settings.scratch_dir = st.text_input(t("settings_scratch_dir", lang), value=settings.scratch_dir)
c1, c2 = st.columns(2)
settings.nproc = int(c1.number_input(t("settings_nproc", lang), min_value=1, max_value=64, value=settings.nproc))
settings.mem_mb = int(c2.number_input(t("settings_mem", lang), min_value=500, max_value=256000, value=settings.mem_mb, step=100))

st.subheader(t("settings_dscf", lang))
st.caption(t("settings_dscf_hint", lang))
c1, c2 = st.columns(2)
settings.dscf_functional = c1.selectbox(
    t("settings_functional", lang),
    options=["pbe", "b3lyp"],
    index=0 if settings.dscf_functional.lower() == "pbe" else 1,
    format_func=lambda x: "PBEPBE (PBE)" if x == "pbe" else "B3LYP",
)
st.caption(t("settings_dscf_g09_hint", lang))
settings.dscf_basis = c2.text_input(t("settings_basis", lang), value=settings.dscf_basis)
settings.xps_fwhm_ev = float(st.number_input(t("settings_fwhm", lang), value=float(settings.xps_fwhm_ev)))
settings.xps_c1s_ref_ev = float(st.number_input(t("settings_c1s_ref", lang), value=float(settings.xps_c1s_ref_ev)))
settings.dscf_apply_c1s_shift = st.checkbox(
    t("settings_c1s_shift", lang),
    value=settings.dscf_apply_c1s_shift,
)

if st.button(t("save", lang)):
    settings.save()
    st.success(t("settings_saved", lang))

st.divider()
st.subheader(t("settings_secrets", lang))
st.caption(t("settings_secrets_hint", lang))
sec = secrets_status()
st.write(t("settings_secrets_path", lang, path=sec["path"]))
if sec["exists"]:
    st.success(t("settings_secrets_found", lang, keys=", ".join(sec["keys"]) or "—"))
else:
    st.info(t("settings_secrets_missing", lang))
if sec["github_token_configured"]:
    source = (
        t("settings_secrets_token_env", lang)
        if sec["github_token_from_env"]
        else t("settings_secrets_token_file", lang)
    )
    st.caption(t("settings_secrets_token_ok", lang, source=source))
else:
    st.caption(t("settings_secrets_token_missing", lang))
if st.button(t("settings_secrets_reload", lang), key="_secrets_reload"):
    clear_secrets_cache()
    load_secrets()
    st.rerun()

st.divider()
render_update_settings(lang)
