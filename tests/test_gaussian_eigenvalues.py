"""Occupied eigenvalue parsing must include Gaussian continuation lines."""

from __future__ import annotations

from pathlib import Path

from src.services.gaussian_parser import parse_gaussian_log


def test_occ_eigenvalue_continuation_lines(tmp_path: Path):
    log = tmp_path / "neutral.log"
    log.write_text(
        """
 SCF Done:  E(RPBE-PBE) =  -79.123456789     A.U. after   12 cycles
 Alpha  occ. eigenvalues --   -11.23456 -11.20000  -0.85000  -0.72000  -0.65000
                         --    -0.54000  -0.43000  -0.32000  -0.21000
 Alpha  virt. eigenvalues --     0.10000   0.20000
 Normal termination of Gaussian
""",
        encoding="utf-8",
    )
    parsed = parse_gaussian_log(log)
    occupied = [o for o in parsed.orbitals if o.occupancy > 0.1]
    assert len(occupied) == 9
    assert occupied[-1].index == 9
