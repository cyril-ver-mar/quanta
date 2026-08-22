"""L4 — export simulated XPS spectra (CSV, Excel, PNG/JPEG/TIFF)."""

from __future__ import annotations

import io
from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go

ExportImageFormat = Literal["png", "jpeg", "tif"]

_MIME = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "tif": "image/tiff",
}


def spectrum_dataframe(x: np.ndarray, y: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"binding_ev": x, "intensity": y})


def spectrum_csv_bytes(x: np.ndarray, y: np.ndarray) -> bytes:
    return spectrum_dataframe(x, y).to_csv(index=False).encode("utf-8")


def spectrum_excel_bytes(
    *,
    curves: dict[str, tuple[np.ndarray, np.ndarray]],
    peaks: pd.DataFrame | None = None,
    parameters: dict[str, object] | None = None,
) -> bytes:
    """One sheet per element curve + optional Peaks / Parameters sheets."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, (x, y) in curves.items():
            spectrum_dataframe(x, y).to_excel(writer, sheet_name=name[:31], index=False)
        if peaks is not None and not peaks.empty:
            peaks.to_excel(writer, sheet_name="Peaks", index=False)
        if parameters:
            pd.DataFrame(
                [{"parameter": k, "value": str(v)} for k, v in parameters.items()]
            ).to_excel(writer, sheet_name="Parameters", index=False)
    return buf.getvalue()


def plotly_spectrum_figure(
    x: np.ndarray,
    y: np.ndarray,
    *,
    title: str,
    x_title: str,
    y_title: str,
    ref_labels: list[str] | None = None,
    ref_bes: list[float] | None = None,
    show_refs: bool = False,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="simulated", line=dict(width=2)))
    if show_refs and ref_bes:
        ymax = float(np.max(y)) if len(y) else 1.0
        for label, be in zip(ref_labels or [], ref_bes, strict=False):
            fig.add_vline(
                x=be,
                line_dash="dot",
                line_color="rgba(180,80,40,0.85)",
                annotation_text=label,
                annotation_position="top",
            )
            fig.add_trace(
                go.Scatter(
                    x=[be],
                    y=[ymax * 1.05],
                    mode="markers",
                    marker=dict(symbol="line-ns-open", size=12, color="rgba(180,80,40,0.9)"),
                    name=label,
                    showlegend=True,
                )
            )
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        xaxis_autorange="reversed",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def figure_to_image_bytes(
    fig: go.Figure,
    *,
    fmt: ExportImageFormat = "png",
    width_in: float = 8.0,
    height_in: float = 5.0,
    dpi: int = 150,
) -> bytes:
    """Rasterize via matplotlib (no Kaleido), XPS-Deconv style."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_m, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    for tr in fig.data:
        if getattr(tr, "type", "") != "scatter":
            continue
        xs = list(tr.x or [])
        ys = list(tr.y or [])
        if not xs:
            continue
        mode = getattr(tr, "mode", "lines") or "lines"
        if "lines" in mode:
            ax.plot(xs, ys, label=tr.name or "", lw=1.8)
        elif "markers" in mode:
            ax.plot(xs, ys, "o", label=tr.name or "", ms=4)
    # Reference vlines from layout shapes if present
    for shape in fig.layout.shapes or []:
        if getattr(shape, "type", "") == "line" and shape.xref == "x":
            ax.axvline(float(shape.x0), color="C3", ls="--", alpha=0.7, lw=1)
    ax.set_xlabel((fig.layout.xaxis.title.text if fig.layout.xaxis.title else None) or "BE (eV)")
    ax.set_ylabel((fig.layout.yaxis.title.text if fig.layout.yaxis.title else None) or "Intensity")
    ax.set_title((fig.layout.title.text if fig.layout.title else None) or "")
    ax.invert_xaxis()
    ax.grid(True, alpha=0.3)
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend(fontsize=8, loc="best")
    fig_m.tight_layout()
    buf = io.BytesIO()
    if fmt == "tif":
        fig_m.savefig(buf, format="png", dpi=dpi)
        plt.close(fig_m)
        from PIL import Image

        img = Image.open(io.BytesIO(buf.getvalue()))
        out = io.BytesIO()
        img.save(out, format="TIFF")
        return out.getvalue()
    fig_m.savefig(buf, format=fmt, dpi=dpi)
    plt.close(fig_m)
    return buf.getvalue()


def image_mime(fmt: ExportImageFormat) -> str:
    return _MIME[fmt]
