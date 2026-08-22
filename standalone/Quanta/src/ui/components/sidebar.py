"""Shared sidebar chrome."""

from __future__ import annotations

import streamlit as st

from src.services.gaussian_runner import gaussian_available
from src.ui.components.update_banner import render_update_banner
from src.utils.cancel import request_hard_stop, request_soft_cancel
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.version import version_label


def render_sidebar(settings: AppSettings) -> AppSettings:
    lang = st.sidebar.selectbox(
        t("language", settings.language),
        options=["en", "ru"],
        index=0 if settings.language == "en" else 1,
        key="lang_select",
    )
    if lang != settings.language:
        settings.language = lang
        settings.save()
        st.rerun()

    mode = t("mode_run", lang) if gaussian_available(settings) else t("mode_analyze", lang)
    st.sidebar.info(mode)
    if not gaussian_available(settings):
        st.sidebar.warning(t("no_gaussian", lang))

    st.sidebar.divider()
    if st.sidebar.button(t("soft_cancel", lang)):
        request_soft_cancel()
        st.sidebar.success("Soft cancel requested")
    if st.sidebar.button(t("hard_stop", lang)):
        request_hard_stop()
        st.sidebar.error("Hard stop requested")
    st.sidebar.caption(version_label())
    render_update_banner(lang)
    return settings
