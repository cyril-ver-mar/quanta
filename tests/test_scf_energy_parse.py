"""SCF Done energy parsing (fixed and Fortran D/E notation)."""

from __future__ import annotations

from pathlib import Path

from src.services.gaussian_parser import final_scf_energy_ha, parse_gaussian_log


def test_scf_done_fortran_d_notation(tmp_path: Path) -> None:
    log = tmp_path / "corehole.log"
    log.write_text(
        """
 SCF Done:  E(UPBE-PBE) =  -0.79123456789D+02     A.U. after   12 cycles
 Normal termination of Gaussian
""",
        encoding="utf-8",
    )
    parsed = parse_gaussian_log(log)
    e = final_scf_energy_ha(parsed)
    assert e is not None
    assert abs(e - (-79.123456789)) < 1e-8


def test_scf_done_plain_decimal(tmp_path: Path) -> None:
    log = tmp_path / "neutral.log"
    log.write_text(
        """
 SCF Done:  E(RPBE-PBE) =  -79.6987024059     A.U. after    8 cycles
 Normal termination of Gaussian
""",
        encoding="utf-8",
    )
    parsed = parse_gaussian_log(log)
    e = final_scf_energy_ha(parsed)
    assert e is not None
    assert abs(e - (-79.6987024059)) < 1e-10
