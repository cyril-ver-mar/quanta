"""L2 — Gaussian input generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def connectivity_from_mol(mol: Any) -> list[str]:
    """Gaussian connectivity section (1-based) from an RDKit molecule."""
    n = int(mol.GetNumAtoms())
    partners: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for bond in mol.GetBonds():
        i = int(bond.GetBeginAtomIdx())
        j = int(bond.GetEndAtomIdx())
        order = float(bond.GetBondTypeAsDouble())
        if j > i:
            partners[i].append((j + 1, order))
        else:
            partners[j].append((i + 1, order))
    lines: list[str] = []
    for atom_i in range(n):
        parts = [str(atom_i + 1)]
        for other, order in sorted(partners[atom_i]):
            parts.append(str(other))
            parts.append(f"{order:.1f}")
        lines.append(" ".join(parts))
    return lines


def ensure_opt_route(route: str, *, has_connectivity: bool) -> str:
    """Keep geom=connectivity only when a connectivity block is present."""
    cleaned = " ".join(route.split())
    if has_connectivity:
        if "geom=connectivity" not in cleaned.lower():
            return f"{cleaned} geom=connectivity"
        return cleaned
    return (
        cleaned.replace("geom=connectivity", "")
        .replace("Geom=Connectivity", "")
        .replace("  ", " ")
        .strip()
    )


def write_gjf(spec: GaussianJobSpec) -> str:
    route = ensure_opt_route(spec.route, has_connectivity=bool(spec.connectivity))
    lines: list[str] = [
        f"%chk={spec.chk_name}",
        f"%nprocshared={spec.nproc}",
        f"%mem={spec.mem_mb}MB",
        f"# {route}",
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
