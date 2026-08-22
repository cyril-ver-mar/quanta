"""Smoke: parse melanine Gaussian log."""

from __future__ import annotations

from pathlib import Path

from src.services.gaussian_parser import final_scf_energy_ha, parse_gaussian_log

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "fixtures" / "melanine" / "MELANINE.LOG"


def test_parse_melanine_log():
    assert LOG.exists()
    result = parse_gaussian_log(LOG)
    assert result.normal_termination
    assert len(result.scf_energies_ha) >= 1
    assert result.orbitals
    assert result.homo_ev is not None
    assert final_scf_energy_ha(result) is not None
