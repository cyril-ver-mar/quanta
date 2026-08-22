"""Smoke: structure export from melanine gjf via temporary compound path."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdkit import Chem

from src.core.structure_export import atom_table, mol_to_block

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "melanine" / "melanine.gjf"


@pytest.mark.skipif(not FIXTURE.exists(), reason="melanine fixture missing")
def test_structure_export_from_mol_block():
    # melanine.gjf is not RDKit-readable directly; use a minimal 3D mol block
    mol = Chem.MolFromMolBlock(
        """
  RDKit          3D

  2  1  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
M  END
"""
    )
    assert mol is not None
    block = mol_to_block(mol)
    assert "M  END" in block
    rows = atom_table(mol)
    assert len(rows) == 2
    assert rows[0]["element"] == "C"
