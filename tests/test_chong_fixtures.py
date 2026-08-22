"""Chong 2007 fixture structures (ethane, hydrazine)."""

from __future__ import annotations

from pathlib import Path

from rdkit import Chem

from src.core.dscf import build_workflow_steps, list_xps_atoms
from src.core.dscf import DscfSettings
from src.services.compound_service import mol_to_atoms
from src.services.fixture_service import load_chong_reference
from src.utils.paths import FIXTURES_DIR

CHONG = FIXTURES_DIR / "chong2007"


def test_chong_mol2_readable() -> None:
    for name, n_atoms, elements in (
        ("ethane", 8, {"C", "H"}),
        ("hydrazine", 6, {"N", "H"}),
    ):
        path = CHONG / f"{name}.mol2"
        assert path.is_file(), path
        mol = Chem.MolFromMol2File(str(path), removeHs=False)
        assert mol is not None
        assert mol.GetNumConformers() >= 1
        assert mol.GetNumAtoms() == n_atoms
        syms = {a.GetSymbol() for a in mol.GetAtoms()}
        assert elements <= syms


def test_chong_reference_and_workflow_steps() -> None:
    ref = load_chong_reference()
    assert "ethane" in ref["molecules"]
    assert ref["molecules"]["ethane"]["chong_obs_ev"]["C1s"] == 290.72
    assert ref["molecules"]["hydrazine"]["chong_obs_ev"]["N1s"] == 406.1

    ethane = Chem.MolFromMol2File(str(CHONG / "ethane.mol2"), removeHs=False)
    assert ethane is not None
    atoms = mol_to_atoms(ethane)
    xps = list_xps_atoms(atoms)
    assert xps == [(0, "C"), (1, "C")]
    steps = build_workflow_steps(atoms, DscfSettings(), job_id=99)
    assert len(steps) == 2 + 2  # OPT + neutral + 2 C core-holes

    hyd = Chem.MolFromMol2File(str(CHONG / "hydrazine.mol2"), removeHs=False)
    assert hyd is not None
    atoms_n = mol_to_atoms(hyd)
    assert list_xps_atoms(atoms_n) == [(0, "N"), (1, "N")]
    steps_n = build_workflow_steps(atoms_n, DscfSettings(), job_id=100)
    assert len(steps_n) == 2 + 2
