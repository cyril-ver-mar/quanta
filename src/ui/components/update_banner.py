"""Update banner: check GitHub Releases once per app launch (Layer 5)."""

from __future__ import annotations

import logging

import streamlit as st

from src.services.app_updater import download_and_apply
from src.utils.github_updates import (
    ERR_BAD_RESPONSE,
    ERR_HTTP,
    ERR_HTTP_403,
    ERR_HTTP_404,
    ERR_NETWORK,
    ERR_NOT_CONFIGURED,
    ERR_SSL,
    ERR_TIMEOUT,
    ERR_UNEXPECTED,
    UpdateStatus,
    check_for_update,
    clear_update_cache,
    resolve_github_repo,
)
from src.utils.i18n import t
from src.utils.paths import ROOT
from src.utils.version import get_version

logger = logging.getLogger(__name__)

_SESSION_STATUS = "_update_status"
_SESSION_DISMISSED = "_update_dismissed"
_SESSION_ERROR = "_update_error"
_SESSION_DONE = "_update_installed"

_ERROR_I18N = {
    ERR_NOT_CONFIGURED: "update_not_configured",
    ERR_NETWORK: "update_check_network",
    ERR_TIMEOUT: "update_check_timeout",
    ERR_SSL: "update_check_ssl",
    ERR_HTTP_404: "update_check_no_releases",
    ERR_HTTP_403: "update_check_rate_limit",
    ERR_HTTP: "update_check_http",
    ERR_BAD_RESPONSE: "update_check_bad_response",
    ERR_UNEXPECTED: "update_check_unexpected",
}


def _status_error_text(status: UpdateStatus, lang: str) -> str | None:
    if not status.error_code:
        return None
    key = _ERROR_I18N.get(status.error_code, "update_check_unexpected")
    return t(
        key,
        lang,
        detail=status.message or status.error_code,
        repo=status.repo or "—",
    )


def _ensure_checked(*, force: bool = False) -> UpdateStatus:
    """Run network check once per Streamlit session (every app launch).

    Disk cache only applies to rate-limit / error backoff — successful
    "latest version" results are never reused from disk, so a newly published
    release appears on the next app start (not an hour later).
    """
    if not force:
        cached = st.session_state.get(_SESSION_STATUS)
        if isinstance(cached, UpdateStatus):
            return cached
    try:
        status = check_for_update(
            local_version=get_version(),
            use_cache=not force,
        )
    except Exception as exc:  # noqa: BLE001 — never block UI on updater
        logger.exception("Update check failed")
        status = UpdateStatus(
            configured=False,
            local_version=get_version(),
            update_available=False,
            latest=None,
            repo=None,
            message=str(exc),
            error_code=ERR_UNEXPECTED,
        )
    st.session_state[_SESSION_STATUS] = status
    return status


def _apply_update(zip_url: str) -> None:
    download_and_apply(zip_url)
    get_version.cache_clear()
    st.session_state[_SESSION_DONE] = True
    st.session_state.pop(_SESSION_ERROR, None)
    clear_update_cache()
    st.session_state[_SESSION_STATUS] = check_for_update(
        local_version=get_version(), use_cache=False
    )


def render_update_banner(lang: str) -> None:
    """On open: ask to upgrade and install in-app (no manual GitHub download)."""
    status = _ensure_checked()
    if st.session_state.get(_SESSION_DISMISSED):
        return

    fail_text = _status_error_text(status, lang)
    if fail_text:
        st.sidebar.warning(fail_text)
        st.sidebar.caption(t("update_check_settings_hint", lang))
        if st.sidebar.button(t("update_dismiss", lang), key="_update_dismiss_btn"):
            st.session_state[_SESSION_DISMISSED] = True
            st.rerun()
        return

    if not status.update_available or status.latest is None:
        return

    latest = status.latest

    @st.dialog(t("update_dialog_title", lang))
    def _upgrade_dialog() -> None:
        st.markdown(
            t("update_available", lang, new=latest.version, old=status.local_version)
        )
        st.caption(t("update_install_help", lang))

        err = st.session_state.get(_SESSION_ERROR)
        if err:
            st.error(t("update_failed", lang, err=err))
        if st.session_state.get(_SESSION_DONE):
            st.success(t("update_installed", lang))
            st.caption(t("update_restart_hint", lang))
            if st.button(t("update_dismiss", lang), key="_upd_dlg_done"):
                st.session_state[_SESSION_DISMISSED] = True
                st.rerun()
            return

        if latest.zip_url:
            c1, c2 = st.columns(2)
            if c1.button(
                t("update_yes_install", lang),
                type="primary",
                use_container_width=True,
                key="_upd_dlg_yes",
            ):
                try:
                    with st.spinner(t("update_working", lang)):
                        _apply_update(latest.zip_url)
                    st.rerun()
                except Exception as exc:
                    logger.exception("Update install failed")
                    st.session_state[_SESSION_ERROR] = str(exc)
                    st.rerun()
            if c2.button(
                t("update_later", lang),
                use_container_width=True,
                key="_upd_dlg_later",
            ):
                st.session_state[_SESSION_DISMISSED] = True
                st.rerun()
        else:
            st.warning(t("update_no_zip", lang))
            st.markdown(f"[{t('update_open_release', lang)}]({latest.html_url})")
            if st.button(t("update_dismiss", lang), key="_upd_dlg_nozip"):
                st.session_state[_SESSION_DISMISSED] = True
                st.rerun()

    # Open modal once per session until the user upgrades or chooses Later.
    _upgrade_dialog()

    # Compact sidebar reminder (install without leaving the app).
    st.sidebar.info(
        t("update_available", lang, new=latest.version, old=status.local_version)
    )
    if st.session_state.get(_SESSION_DONE):
        st.sidebar.success(t("update_installed", lang))
        st.sidebar.caption(t("update_restart_hint", lang))
    err = st.session_state.get(_SESSION_ERROR)
    if err:
        st.sidebar.error(t("update_failed", lang, err=err))
    if latest.zip_url and not st.session_state.get(_SESSION_DONE):
        if st.sidebar.button(t("update_yes_install", lang), key="_update_sidebar_install"):
            try:
                with st.spinner(t("update_working", lang)):
                    _apply_update(latest.zip_url)
                st.rerun()
            except Exception as exc:
                logger.exception("Update install failed")
                st.session_state[_SESSION_ERROR] = str(exc)
                st.rerun()
    if st.sidebar.button(t("update_later", lang), key="_update_dismiss_btn2"):
        st.session_state[_SESSION_DISMISSED] = True
        st.rerun()


def render_update_settings(lang: str) -> None:
    """Settings section: status + force re-check."""
    st.subheader(t("update_section", lang))
    status = _ensure_checked()
    repo_path = ROOT / "GITHUB_REPO"
    if status.error_code == ERR_NOT_CONFIGURED:
        st.caption(
            t(
                "update_repo_file_exists",
                lang,
                path=str(repo_path),
                exists=repo_path.is_file(),
            )
        )
        resolved = resolve_github_repo()
        if repo_path.is_file() and resolved is None:
            st.warning(t("update_repo_parse_fail", lang))
        elif not repo_path.is_file():
            st.warning(t("update_repo_create_hint", lang, name=repo_path.name))
    fail_text = _status_error_text(status, lang)
    if fail_text:
        st.warning(fail_text)
        if status.message:
            st.caption(t("update_check_detail", lang, detail=status.message))
        if status.repo:
            st.write(t("update_repo", lang, repo=status.repo))
        st.write(t("update_local_only", lang, local=status.local_version))
    else:
        st.write(t("update_repo", lang, repo=status.repo or "—"))
        st.write(
            t(
                "update_local_remote",
                lang,
                local=status.local_version,
                remote=(status.latest.version if status.latest else "—"),
            )
        )
        if status.update_available and status.latest:
            latest = status.latest
            st.caption(t("update_install_help", lang))
            if latest.zip_url:
                if st.button(t("update_yes_install", lang), key="_settings_update_install"):
                    try:
                        with st.spinner(t("update_working", lang)):
                            _apply_update(latest.zip_url)
                        st.rerun()
                    except Exception as exc:
                        logger.exception("Update install failed")
                        st.error(t("update_failed", lang, err=str(exc)))
            else:
                st.warning(t("update_no_zip", lang))
                st.markdown(f"[{t('update_open_release', lang)}]({latest.html_url})")
        elif status.latest:
            st.success(t("update_up_to_date", lang))

    if st.button(t("update_check_now", lang), key="_update_check_now"):
        clear_update_cache()
        st.session_state.pop(_SESSION_STATUS, None)
        st.session_state.pop(_SESSION_DISMISSED, None)
        st.session_state.pop(_SESSION_ERROR, None)
        st.session_state[_SESSION_STATUS] = check_for_update(
            local_version=get_version(), use_cache=False
        )
        st.rerun()
