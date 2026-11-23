"""Periodic structures, supercells, and symmetry-inequivalent XPS sites.

Structures are read with ASE (CIF, POSCAR, extxyz). Site symmetry uses spglib
when it is installed, and a minimum-image neighbor fingerprint otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

XPS_ELEMENTS = ("C", "N", "O")

_ATOMIC_NUMBERS = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9,
    "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17,
    "Ar": 18, "K": 19, "Ca": 20,
}


@dataclass(frozen=True)
class PeriodicStructure:
    symbols: tuple[str, ...]
    positions: tuple[tuple[float, float, float], ...]  # Å, Cartesian
    cell: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]
    pbc: tuple[bool, bool, bool] = (True, True, True)

    def __post_init__(self) -> None:
        cell = np.asarray(self.cell, dtype=float)
        if cell.shape != (3, 3):
            raise ValueError("A periodic structure needs a 3×3 cell in Ångström")
        if abs(float(np.linalg.det(cell))) < 1e-8:
            raise ValueError("The cell volume is zero. CIF/POSCAR/extxyz must include a lattice.")

    @property
    def n_atoms(self) -> int:
        return len(self.symbols)


@dataclass(frozen=True)
class CrystalSite:
    """One symmetry-inequivalent C/N/O site in the input cell."""

    index: int  # 0-based index in the input cell (and in the first supercell image)
    element: str
    multiplicity: int
    equivalents: tuple[int, ...]


def structure_from_arrays(
    symbols: list[str],
    positions: list[list[float]] | np.ndarray,
    cell: list[list[float]] | np.ndarray,
    pbc: list[bool] | tuple[bool, bool, bool] = (True, True, True),
) -> PeriodicStructure:
    pos = np.asarray(positions, dtype=float)
    if pos.ndim != 2 or pos.shape[1] != 3:
        raise ValueError("Positions must be an (N, 3) array in Ångström")
    if len(symbols) != len(pos):
        raise ValueError("Symbol list and positions have different lengths")
    cell_a = np.asarray(cell, dtype=float)
    return PeriodicStructure(
        symbols=tuple(str(s) for s in symbols),
        positions=tuple(tuple(float(x) for x in row) for row in pos),
        cell=tuple(tuple(float(x) for x in row) for row in cell_a),  # type: ignore[arg-type]
        pbc=(bool(pbc[0]), bool(pbc[1]), bool(pbc[2])),
    )


def structure_from_meta(meta: dict) -> PeriodicStructure:
    return structure_from_arrays(
        list(meta["symbols"]),
        meta["positions"],
        meta["cell"],
        meta.get("pbc") or (True, True, True),
    )


def formula_from_symbols(symbols: list[str] | tuple[str, ...]) -> str:
    counts: dict[str, int] = {}
    for sym in symbols:
        counts[sym] = counts.get(sym, 0) + 1
    hill = [el for el in ("C", "H") if el in counts]
    hill.extend(sorted(el for el in counts if el not in ("C", "H")))
    parts = []
    for el in hill:
        n = counts[el]
        parts.append(el if n == 1 else f"{el}{n}")
    return "".join(parts)


def element_counts(symbols: list[str] | tuple[str, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sym in symbols:
        counts[sym] = counts.get(sym, 0) + 1
    return counts


def read_periodic_structure(path: str, source_name: str | None = None) -> PeriodicStructure:
    """Read CIF / POSCAR / extxyz via ASE. Raises a clear error if ASE is missing."""
    try:
        from ase.io import read
    except ImportError as exc:
        raise ImportError(
            "Reading CIF, POSCAR, or extxyz needs ASE "
            "(installed with GPAW: conda install -c conda-forge gpaw ase). "
            f"Import failed: {exc}"
        ) from exc
    label = (source_name or path).lower()
    fmt = None
    if Path(label).name in {"poscar", "contcar"} or label.endswith(".poscar") or label.endswith(".vasp"):
        fmt = "vasp"
    elif label.endswith(".cif"):
        fmt = "cif"
    elif label.endswith(".extxyz") or label.endswith(".xyz"):
        fmt = "extxyz"
    atoms = read(str(path), format=fmt) if fmt else read(str(path))
    if isinstance(atoms, list):
        if not atoms:
            raise ValueError(f"No structure in {path}")
        atoms = atoms[-1]
    if atoms is None:
        raise ValueError(f"ASE could not read {path}")
    cell = np.asarray(atoms.cell.array, dtype=float)
    if atoms.cell.rank < 3 or abs(float(np.linalg.det(cell))) < 1e-8:
        raise ValueError(
            f"{path} has no periodic cell. GPAW XPS needs CIF, POSCAR, or extxyz with a lattice."
        )
    return structure_from_arrays(
        list(atoms.get_chemical_symbols()),
        atoms.get_positions(),
        cell,
        [bool(v) for v in atoms.pbc],
    )


def parse_int_triple(text: str, *, name: str) -> tuple[int, int, int]:
    parts = [p.strip() for p in (text or "").replace("x", ",").split(",") if p.strip()]
    if len(parts) != 3:
        raise ValueError(f"{name} must be three integers, for example 2,2,1")
    values = tuple(int(p) for p in parts)
    if any(v < 1 for v in values):
        raise ValueError(f"{name} entries must be ≥ 1, got {values}")
    return values  # type: ignore[return-value]


def make_supercell(structure: PeriodicStructure, repeat: tuple[int, int, int]) -> PeriodicStructure:
    """Repeat the cell. Atoms of the original cell stay at indices ``0 … N-1``.

    That matches the usual ASE ``atoms * (n1, n2, n3)`` ordering, so a
    core hole on primitive site ``i`` is atom ``i`` of the supercell.
    """
    nx, ny, nz = repeat
    cell = np.asarray(structure.cell, dtype=float)
    symbols: list[str] = []
    positions: list[list[float]] = []
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                shift = ix * cell[0] + iy * cell[1] + iz * cell[2]
                for sym, pos in zip(structure.symbols, structure.positions, strict=True):
                    symbols.append(sym)
                    positions.append((np.asarray(pos, dtype=float) + shift).tolist())
    new_cell = cell.copy()
    new_cell[0] *= nx
    new_cell[1] *= ny
    new_cell[2] *= nz
    return structure_from_arrays(symbols, positions, new_cell, structure.pbc)


def _fractional(positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    return np.linalg.solve(cell.T, positions.T).T


def _mic_distance(a: np.ndarray, b: np.ndarray, cell: np.ndarray) -> float:
    frac = np.linalg.solve(cell.T, b - a)
    frac -= np.round(frac)
    return float(np.linalg.norm(frac @ cell))


def _fingerprint_groups(
    structure: PeriodicStructure,
    *,
    tol: float = 0.05,
) -> np.ndarray:
    """Return a representative index for every atom (fingerprint equivalence)."""
    cell = np.asarray(structure.cell, dtype=float)
    pos = np.asarray(structure.positions, dtype=float)
    keys: list[tuple] = []
    for i, sym in enumerate(structure.symbols):
        neighbors = []
        for j, other in enumerate(structure.symbols):
            if i == j:
                continue
            dist = _mic_distance(pos[i], pos[j], cell)
            neighbors.append((other, round(dist / tol) * tol))
        keys.append((sym, tuple(sorted(neighbors))))
    groups = np.arange(len(keys))
    first: dict[tuple, int] = {}
    for i, key in enumerate(keys):
        if key not in first:
            first[key] = i
        groups[i] = first[key]
    return groups


def _spglib_groups(structure: PeriodicStructure, symprec: float) -> np.ndarray | None:
    try:
        import spglib
    except ImportError:
        return None
    cell = np.asarray(structure.cell, dtype=float)
    pos = np.asarray(structure.positions, dtype=float)
    try:
        frac = _fractional(pos, cell)
    except np.linalg.LinAlgError:
        return None
    numbers = []
    for sym in structure.symbols:
        z = _ATOMIC_NUMBERS.get(sym)
        if z is None:
            return None
        numbers.append(z)
    dataset = spglib.get_symmetry_dataset((cell, frac, numbers), symprec=symprec)
    if dataset is None:
        return None
    equiv = getattr(dataset, "equivalent_atoms", None)
    if equiv is None and isinstance(dataset, dict):
        equiv = dataset.get("equivalent_atoms")
    if equiv is None:
        return None
    return np.asarray(equiv, dtype=int)


def inequivalent_sites(
    structure: PeriodicStructure,
    *,
    elements: tuple[str, ...] = ("C", "N"),
    symprec: float = 1e-3,
) -> list[CrystalSite]:
    """Symmetry-inequivalent sites of the requested elements, input-cell indices."""
    groups = _spglib_groups(structure, symprec)
    if groups is None or len(groups) != structure.n_atoms:
        groups = _fingerprint_groups(structure)
    wanted = {el.strip() for el in elements if el.strip()}
    buckets: dict[int, list[int]] = {}
    for i, rep in enumerate(groups):
        if structure.symbols[i] not in wanted:
            continue
        buckets.setdefault(int(rep), []).append(i)
    sites: list[CrystalSite] = []
    for members in buckets.values():
        members = sorted(members)
        rep = members[0]
        # If spglib's representative is not the lowest index, still use the
        # lowest index in this cell so the supercell image is stable.
        sites.append(
            CrystalSite(
                index=rep,
                element=structure.symbols[rep],
                multiplicity=len(members),
                equivalents=tuple(members),
            )
        )
    sites.sort(key=lambda s: s.index)
    return sites
