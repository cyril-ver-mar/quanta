"""L2 — Gaussian input generation."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_ROUTE = "opt pbe/6-31g(d) geom=connectivity int=ultrafine"


@dataclass
class GaussianJobSpec:
    title: str
    charge: int
    multiplicity: int
    atoms: list[tuple[str, float, float, float]]
    connectivity: list[str] | None = None
    chk_name: str = "job.chk"
    nproc: int = 4
    mem_mb: int = 1500
    route: str = DEFAULT_ROUTE


def write_gjf(spec: GaussianJobSpec) -> str:
    lines: list[str] = [
        f"%chk={spec.chk_name}",
        f"%nprocshared={spec.nproc}",
        f"%mem={spec.mem_mb}MB",
        f"# {spec.route}",
        "",
        spec.title,
        "",
        f"{spec.charge} {spec.multiplicity}",
    ]
    for sym, x, y, z in spec.atoms:
        lines.append(f" {sym:<2} {x:16.8f} {y:16.8f} {z:16.8f}")
    lines.append("")
    if spec.connectivity:
        lines.extend(spec.connectivity)
        lines.append("")
    return "\n".join(lines) + "\n"


def write_checkpoint_job(
    *,
    title: str,
    charge: int,
    multiplicity: int,
    route: str,
    oldchk: str,
    chk: str,
    nproc: int,
    mem_mb: int,
    alter_swap: tuple[int, int] | None = None,
) -> str:
    """SP from checkpoint; optional Guess=Alter swap pair (core orbital, HOMO)."""
    lines: list[str] = [
        f"%oldchk={oldchk}",
        f"%chk={chk}",
        f"%nprocshared={nproc}",
        f"%mem={mem_mb}MB",
        f"# {route}",
        "",
        title,
        "",
        f"{charge} {multiplicity}",
        "",
    ]
    if alter_swap is not None:
        a, b = alter_swap
        lines.extend(["Alter", f"swap {a},{b}", "end", ""])
    return "\n".join(lines) + "\n"
