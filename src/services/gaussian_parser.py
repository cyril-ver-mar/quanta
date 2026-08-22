"""L2 / service helper — parse Gaussian 09 text logs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.core.models import Orbital

SCF_RE = re.compile(r"SCF Done:\s+E\((\w+)\)\s*=\s*([-\d.]+)", re.I)
OPT_RE = re.compile(r"Optimized Parameters", re.I)
NORMAL_RE = re.compile(r"Normal termination of Gaussian", re.I)
ERROR_RE = re.compile(r"Error termination", re.I)
STEP_RE = re.compile(r"Step number\s+(\d+)", re.I)
OCC_LINE_RE = re.compile(r"Alpha\s+occ\.\s+eigenvalues\s+--\s+(.+)", re.I)
VIRT_LINE_RE = re.compile(r"Alpha\s+virt\.\s+eigenvalues\s+--\s+(.+)", re.I)
HOMO_LUMO_GAP_HINT = re.compile(r"eigenvalues", re.I)


@dataclass
class ParseResult:
    success: bool
    normal_termination: bool
    scf_energies_ha: list[float] = field(default_factory=list)
    opt_steps: int = 0
    orbitals: list[Orbital] = field(default_factory=list)
    homo_ev: float | None = None
    lumo_ev: float | None = None
    gap_ev: float | None = None
    method: str = ""
    raw_errors: list[str] = field(default_factory=list)
    progress_estimate: float = 0.0


def _floats(chunk: str) -> list[float]:
    return [float(x) for x in chunk.split() if re.fullmatch(r"[+-]?\d+\.\d+", x)]


def parse_gaussian_log(path: Path | str) -> ParseResult:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    result = ParseResult(success=False, normal_termination=bool(NORMAL_RE.search(text)))
    if ERROR_RE.search(text):
        result.raw_errors.append("Error termination found in log")

    for m in SCF_RE.finditer(text):
        result.method = m.group(1)
        result.scf_energies_ha.append(float(m.group(2)))

    steps = STEP_RE.findall(text)
    result.opt_steps = int(steps[-1]) if steps else len(result.scf_energies_ha)

    # Orbitals after the last SCF Done (final electronic structure)
    occ_vals: list[float] = []
    virt_vals: list[float] = []
    last_scf = None
    for m in SCF_RE.finditer(text):
        last_scf = m
    tail_text = text[last_scf.end() :] if last_scf is not None else text
    for m in OCC_LINE_RE.finditer(tail_text):
        occ_vals.extend(_floats(m.group(1)))
    for m in VIRT_LINE_RE.finditer(tail_text):
        virt_vals.extend(_floats(m.group(1)))

    idx = 1
    for e in occ_vals:
        result.orbitals.append(Orbital(index=idx, energy_ha=e, occupancy=2.0))
        idx += 1
    for e in virt_vals:
        result.orbitals.append(Orbital(index=idx, energy_ha=e, occupancy=0.0))
        idx += 1

    occupied = [o for o in result.orbitals if o.occupancy > 0]
    virtual = [o for o in result.orbitals if o.occupancy == 0]
    if occupied:
        result.homo_ev = occupied[-1].energy_ev
    if virtual:
        result.lumo_ev = virtual[0].energy_ev
    if result.homo_ev is not None and result.lumo_ev is not None:
        result.gap_ev = result.lumo_ev - result.homo_ev

    # Progress: OPT done if Optimized Parameters or Normal termination
    if result.normal_termination:
        result.progress_estimate = 1.0
    elif OPT_RE.search(text):
        result.progress_estimate = 0.85
    elif result.opt_steps:
        result.progress_estimate = min(0.8, 0.1 + 0.05 * result.opt_steps)
    elif result.scf_energies_ha:
        result.progress_estimate = 0.2
    else:
        result.progress_estimate = 0.05

    result.success = result.normal_termination and not result.raw_errors
    return result


def final_scf_energy_ha(result: ParseResult) -> float | None:
    """Last SCF Done energy in the log (Ha)."""
    if not result.scf_energies_ha:
        return None
    return result.scf_energies_ha[-1]


def estimate_eta_seconds(result: ParseResult, elapsed_s: float) -> float | None:
    p = result.progress_estimate
    if p <= 0.05 or elapsed_s <= 0:
        return None
    if p >= 0.99:
        return 0.0
    return elapsed_s * (1.0 - p) / p
