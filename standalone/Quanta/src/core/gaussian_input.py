"""L2 — Gaussian input generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROUTE = "opt PBEPBE/6-31g(d) geom=connectivity Integral=UltraFine"

# Windows Gaussian often chokes on non-ASCII in the title / Link0 lines.
_ASCII_REPLACEMENTS = (
    ("·", "-"),
    ("Δ", "Delta-"),
    ("δ", "delta-"),
    ("–", "-"),
    ("—", "-"),
    ("′", "'"),
    ("μ", "u"),
    ("Å", "A"),
)


def ascii_safe(text: str) -> str:
    """Reduce text to Latin-1/ASCII safe for Gaussian input files."""
    out = text or ""
    for src, dst in _ASCII_REPLACEMENTS:
        out = out.replace(src, dst)
    return out.encode("ascii", "replace").decode("ascii")


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


def format_route_lines(route: str, *, max_len: int = 72) -> list[str]:
    """Split a route into ``# …`` lines under Gaussian's ~80-char input limit.

    G09 silently breaks overlong route lines mid-token (e.g. ``guess`` → ``g`` /
    ``uess``), which yields QPErr syntax errors.
    """
    tokens = ascii_safe(" ".join((route or "").split())).split()
    if not tokens:
        return ["#"]
    lines: list[str] = []
    current = "#"
    for tok in tokens:
        candidate = f"{current} {tok}" if current != "#" else f"# {tok}"
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current != "#":
            lines.append(current)
        current = f"# {tok}"
        if len(current) > max_len:
            lines.append(current)
            current = "#"
    if current != "#":
        lines.append(current)
    return lines


def join_gjf_lines(lines: list[str]) -> str:
    """Join input lines with LF; writers convert to CRLF for G09W."""
    return "\n".join(lines) + "\n"


def write_gaussian_file(path: Path | str, text: str) -> None:
    """Write a ``.gjf`` with CRLF line endings (required by G09W on Windows).

    LF-only files make G09W glue a following ``#`` route line onto the previous
    line (``…checkpoint #``), which triggers QPErr.
    """
    p = Path(path)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    p.write_text(normalized, encoding="ascii", errors="replace", newline="\r\n")


def write_gjf(spec: GaussianJobSpec) -> str:
    route = ensure_opt_route(spec.route, has_connectivity=bool(spec.connectivity))
    lines: list[str] = [
        f"%chk={ascii_safe(spec.chk_name)}",
        f"%nprocshared={spec.nproc}",
        f"%mem={spec.mem_mb}MB",
    ]
    lines.extend(format_route_lines(route))
    lines.extend(
        [
            "",
            ascii_safe(spec.title),
            "",
            f"{spec.charge} {spec.multiplicity}",
        ]
    )
    for sym, x, y, z in spec.atoms:
        lines.append(f" {sym:<2} {x:16.8f} {y:16.8f} {z:16.8f}")
    lines.append("")
    if spec.connectivity:
        lines.extend(spec.connectivity)
        lines.append("")
    return join_gjf_lines(lines)


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
    """SP from checkpoint; optional Guess=Alter swap pair (core orbital, HOMO).

    G09W often rejects ``%oldchk=``. The runner copies ``oldchk`` → ``chk`` on disk
    before launch; the input only references ``%chk=``.
    """
    _ = oldchk  # staged by GaussianRunner before launch
    lines: list[str] = [
        f"%chk={ascii_safe(chk)}",
        f"%nprocshared={nproc}",
        f"%mem={mem_mb}MB",
    ]
    lines.extend(format_route_lines(route))
    lines.extend(
        [
            "",
            ascii_safe(title),
            "",
            f"{charge} {multiplicity}",
            "",
        ]
    )
    if alter_swap is not None:
        a, b = alter_swap
        lines.extend(["Alter", f"swap {a},{b}", "end", ""])
    return join_gjf_lines(lines)
