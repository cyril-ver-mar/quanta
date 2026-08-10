"""Smoke: parse melanine Gaussian log and assign cores."""

from __future__ import annotations

from pathlib import Path

from src.core.xps import apply_yamada_corrections, assign_core_levels, XpsSettings
from src.services.gaussian_parser import parse_gaussian_log

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "fixtures" / "melanine" / "MELANINE.LOG"


def test_parse_melanine_log():
    assert LOG.exists()
    result = parse_gaussian_log(LOG)
    assert result.normal_termination
    assert len(result.scf_energies_ha) >= 1
    assert result.orbitals
    assert result.homo_ev is not None


def test_melanine_core_levels():
    result = parse_gaussian_log(LOG)
    levels = assign_core_levels(result.orbitals, element_counts={"C": 3, "N": 6})
    levels = apply_yamada_corrections(levels, XpsSettings())
    elements = {lv.element for lv in levels}
    assert "C" in elements
    assert "N" in elements
    assert all(lv.binding_ev_final > 0 for lv in levels)
