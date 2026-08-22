"""L5 — interactive 3D molecule viewer (py3Dmol)."""

from __future__ import annotations

import streamlit.components.v1 as components

STYLE_MAP = {
    "stick": {"stick": {"radius": 0.15}},
    "ballstick": {"stick": {"radius": 0.1}, "sphere": {"scale": 0.25}},
    "sphere": {"sphere": {"scale": 0.3}},
    "line": {"line": {}},
}


def render_molecule_3d(
    mol_block: str,
    fmt: str = "mol",
    style: str = "stick",
    width: int = 800,
    height: int = 480,
    background: str = "0xF7F8FA",
) -> None:
    import py3Dmol

    view = py3Dmol.view(width=width, height=height)
    view.addModel(mol_block, fmt)
    view.setStyle({}, STYLE_MAP.get(style, STYLE_MAP["stick"]))
    view.setBackgroundColor(background)
    view.zoomTo()
    components.html(view._make_html(), height=height + 12, scrolling=False)
