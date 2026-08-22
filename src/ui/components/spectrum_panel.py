"""L5 — simulated XPS spectrum controls + exports on Results."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.core.xps import PEAK_PROFILES, SpectrumParams, levels_from_summary_rows, simulate_spectrum
from src.core.xps_references import reference_sticks_for_job
from src.services.spectrum_export import (
    figure_to_image_bytes,
    image_mime,
    plotly_spectrum_figure,
    spectrum_csv_bytes,
    spectrum_excel_bytes,
)
from src.utils.i18n import t


def render_simulated_spectra(
    summary: dict[str, Any],
    *,
    lang: str,
    compound_name: str | None,
    default_fwhm: float,
) -> None:
    st.subheader(t("results_spectra", lang))

    c1, c2, c3, c4 = st.columns(4)
    profile = c1.selectbox(
        t("results_profile", lang),
        options=list(PEAK_PROFILES),
        index=list(PEAK_PROFILES).index("pseudovoigt"),
        format_func=lambda p: t(f"results_profile_{p}", lang),
        key="_xps_profile",
    )
    fwhm = c2.number_input(
        t("results_fwhm", lang),
        min_value=0.2,
        max_value=5.0,
        value=float(default_fwhm),
        step=0.1,
        key="_xps_fwhm",
    )
    fraction = c3.slider(
        t("results_fraction", lang),
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        key="_xps_fraction",
        help=t("results_fraction_help", lang),
    )
    show_refs = c4.toggle(t("results_show_refs", lang), value=True, key="_xps_show_refs")

    params = SpectrumParams(profile=profile, fwhm_ev=float(fwhm), fraction=float(fraction))
    levels = levels_from_summary_rows(list(summary.get("core_levels") or []))
    peaks_df = pd.DataFrame(summary.get("core_levels") or [])
    curves: dict[str, tuple] = {}

    for element in ("C", "N", "O"):
        x, y = simulate_spectrum(levels, element, params=params)
        if len(x) == 0:
            continue
        curves[f"{element}1s"] = (x, y)
        sticks = reference_sticks_for_job(element, compound_name=compound_name)
        fig = plotly_spectrum_figure(
            x,
            y,
            title=t("results_spectrum_title", lang, element=element),
            x_title=t("results_be_axis", lang),
            y_title=t("results_intensity_axis", lang),
            ref_labels=[s.label for s in sticks],
            ref_bes=[s.be_ev for s in sticks],
            show_refs=show_refs and bool(sticks),
        )
        st.plotly_chart(fig, use_container_width=True)

        if show_refs and sticks:
            st.caption(
                t("results_refs_caption", lang)
                + " "
                + "; ".join(f"{s.label}={s.be_ev:.2f} eV ({s.source})" for s in sticks[:8])
                + ("…" if len(sticks) > 8 else "")
            )

        b1, b2, b3 = st.columns(3)
        b1.download_button(
            t("results_dl_spec_csv", lang, element=element),
            data=spectrum_csv_bytes(x, y),
            file_name=f"xps_{element}1s.csv",
            mime="text/csv",
            key=f"_dl_csv_{element}",
        )
        for fmt, col in (("png", b2), ("jpeg", b3)):
            try:
                img = figure_to_image_bytes(fig, fmt=fmt)  # type: ignore[arg-type]
                col.download_button(
                    t("results_dl_spec_img", lang, element=element, fmt=fmt.upper()),
                    data=img,
                    file_name=f"xps_{element}1s.{'jpg' if fmt == 'jpeg' else fmt}",
                    mime=image_mime(fmt),  # type: ignore[arg-type]
                    key=f"_dl_{fmt}_{element}",
                )
            except Exception as exc:
                col.caption(f"{fmt}: {exc}")

    if curves:
        st.markdown(t("results_export_all", lang))
        e1, e2, e3 = st.columns(3)
        try:
            xlsx = spectrum_excel_bytes(
                curves=curves,
                peaks=peaks_df if not peaks_df.empty else None,
                parameters={
                    "profile": profile,
                    "fwhm_ev": fwhm,
                    "fraction": fraction,
                    "compound": compound_name or "",
                },
            )
            e1.download_button(
                t("results_dl_excel", lang),
                data=xlsx,
                file_name="xps_spectra.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="_dl_xlsx_all",
            )
        except ImportError as exc:
            e1.caption(str(exc))
        except Exception as exc:
            e1.caption(f"Excel: {exc}")
        # TIFF of first available element
        first_el = next(iter(curves))
        x0, y0 = curves[first_el]
        el0 = first_el.replace("1s", "")
        sticks0 = reference_sticks_for_job(el0, compound_name=compound_name)
        fig0 = plotly_spectrum_figure(
            x0,
            y0,
            title=t("results_spectrum_title", lang, element=el0),
            x_title=t("results_be_axis", lang),
            y_title=t("results_intensity_axis", lang),
            ref_labels=[s.label for s in sticks0],
            ref_bes=[s.be_ev for s in sticks0],
            show_refs=show_refs and bool(sticks0),
        )
        try:
            tiff = figure_to_image_bytes(fig0, fmt="tif")
            e2.download_button(
                t("results_dl_tiff", lang),
                data=tiff,
                file_name=f"xps_{first_el}.tif",
                mime=image_mime("tif"),
                key="_dl_tif_all",
            )
        except Exception as exc:
            e2.caption(str(exc))
        e3.caption(t("results_export_hint", lang))
