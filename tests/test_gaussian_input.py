"""Tests for Gaussian input helpers and CLI resolution."""

from __future__ import annotations

from pathlib import Path

from rdkit import Chem

from src.core.gaussian_input import (
    GaussianJobSpec,
    connectivity_from_mol,
    ensure_opt_route,
    write_gjf,
)
from src.services.gaussian_runner import _coerce_cli_exe


def test_write_gjf_includes_connectivity_for_ethane() -> None:
    mol = Chem.MolFromMol2File("fixtures/chong2007/ethane.mol2", removeHs=False)
    assert mol is not None
    conn = connectivity_from_mol(mol)
    assert conn[0].startswith("1 ")
    assert "2 1.0" in conn[0]
    text = write_gjf(
        GaussianJobSpec(
            title="ethane",
            charge=0,
            multiplicity=1,
            atoms=[(a.GetSymbol(), 0.0, 0.0, 0.0) for a in mol.GetAtoms()],
            connectivity=conn,
            route="opt pbe/6-31g(d) geom=connectivity int=ultrafine",
        )
    )
    assert "geom=connectivity" in text
    assert "\n1 2 1.0" in text or text.splitlines()[-3].startswith("1 ")


def test_ensure_opt_route_strips_connectivity_when_missing() -> None:
    assert "geom=connectivity" not in ensure_opt_route(
        "opt pbe/6-31g(d) geom=connectivity int=ultrafine",
        has_connectivity=False,
    )
    assert "geom=connectivity" in ensure_opt_route(
        "opt pbe/6-31g(d) int=ultrafine",
        has_connectivity=True,
    )


def test_coerce_gui_to_cli(tmp_path: Path) -> None:
    gui = tmp_path / "g09w.exe"
    cli = tmp_path / "g09.exe"
    gui.write_bytes(b"x")
    cli.write_bytes(b"x")
    assert _coerce_cli_exe(str(gui)) == str(cli)


def test_coerce_gui_alone_returns_none(tmp_path: Path) -> None:
    gui = tmp_path / "g09w.exe"
    gui.write_bytes(b"x")
    assert _coerce_cli_exe(str(gui)) is None
