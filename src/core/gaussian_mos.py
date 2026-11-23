"""Gaussian 09 MO coefficients, 1s assignment, and core-hole checks.

``pop=full`` prints the MO coefficient matrix. Core 1s orbitals are assigned
from the 1s basis population on each atom. Symmetry-equivalent atoms share
delocalized canonical 1s MOs; those subspaces are localized (Pipek–Mezey on
the 1s functions) and written back with ``Guess=Cards`` so the hole sits on
one atom. ``Guess=Alter`` is kept when the canonical 1s is already localized.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

from src.core.models import Orbital

# 1s eigenvalue windows (Hartree). Valence eigenvalues of C/N/O sit near 0 to -2.
CORE_WINDOWS_HA: dict[str, tuple[float, float]] = {
    "O": (-25.0, -16.0),
    "N": (-16.5, -12.0),
    "C": (-12.5, -8.0),
}

# Raw ΔSCF 1s binding-energy windows (eV). Wide enough for a functional/basis
# offset, narrow enough that a valence hole (~10–40 eV) or a mis-labelled
# N1s (~400 eV) on carbon is rejected.
BE_WINDOWS_EV: dict[str, tuple[float, float]] = {
    "C": (250.0, 340.0),
    "N": (370.0, 460.0),
    "O": (500.0, 590.0),
}

_LOCALIZED_POP = 0.80
_MIN_POP = 0.50
_CORE_ENERGY_CUTOFF_HA = -5.0

_BASIS_LINE = re.compile(
    r"^\s*(\d+)\s+"
    r"(?:(\d+)\s+([A-Z][a-z]?)\s+)?"
    r"([0-9A-Za-z]+)\s+"
    r"((?:[-+]?\d+\.\d+(?:[DdEe][+-]?\d+)?\s*)+)$"
)
_S2_RE = re.compile(r"S\*\*2 before annihilation\s+([-+]?\d+\.\d+)", re.I)
_S2_ALT_RE = re.compile(r"<S\*\*2>=\s*([-+]?\d+\.\d+)")
_SPIN_HEADER = "Mulliken charges and spin densities:"
_CHARGE_HEADER = "Mulliken atomic charges:"
_ATOM_LINE = re.compile(
    r"^\s*(\d+)\s+([A-Z][a-z]?)\s+([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s*$"
)
_CHARGE_LINE = re.compile(r"^\s*(\d+)\s+([A-Z][a-z]?)\s+([-+]?\d+\.\d+)\s*$")


@dataclass
class BasisFn:
    index: int  # 1-based basis function
    atom_index: int  # 0-based
    element: str
    shell: str


@dataclass
class MoSet:
    """One spin's MO coefficient matrix from the last ``pop=full`` block."""

    basis: list[BasisFn]
    eigenvalues: np.ndarray  # (nmo,) Hartree
    coefficients: np.ndarray  # (nbf, nmo), column j is MO j+1
    occupied: np.ndarray  # (nmo,) True when Gaussian labelled the MO ``O``
    spin: str


@dataclass
class GaussianPopulation:
    alpha: MoSet | None = None
    beta: MoSet | None = None
    s2: float | None = None
    spin_density: list[float] | None = None  # index 0 = atom 1
    mulliken_charge: list[float] | None = None


@dataclass
class CoreOrbitalMap:
    """Atom (0-based) → MO index (1-based) after optional 1s localization."""

    by_atom: dict[int, int]
    population: dict[int, float]
    guess_style: str  # "alter" (canonical MO already local) or "cards"
    coefficients: np.ndarray | None  # localized (nbf, nmo); None if alter
    eigenvalues: np.ndarray | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class CoreHoleVerdict:
    ok: bool
    failures: list[str]
    warnings: list[str]
    s2: float | None = None
    spin_density: float | None = None
    alpha_1s_population: float | None = None
    beta_1s_population: float | None = None

    @property
    def message(self) -> str:
        parts = list(self.failures)
        if self.warnings:
            parts.append("Notes: " + "; ".join(self.warnings))
        return " ".join(parts).strip()


def _floats(chunk: str) -> list[float]:
    out: list[float] = []
    for tok in chunk.split():
        try:
            out.append(float(tok.replace("D", "E").replace("d", "e")))
        except ValueError:
            continue
    return out


def _parse_coefficient_section(lines: list[str], start: int, stop: int) -> MoSet:
    eigenvalues: list[float] = []
    occupied_flags: list[bool] = []
    columns: list[list[float]] = []
    basis: list[BasisFn] = []
    atom_index = -1
    element = "?"
    first_block = True
    current: list[list[float]] | None = None
    previous = ""

    for line in lines[start + 1 : stop]:
        if "Density Matrix" in line or "Mulliken" in line or "Molecular Orbital Coefficients" in line:
            break
        if "Eigenvalues --" in line:
            vals = _floats(line.split("--", 1)[1])
            if current is not None:
                first_block = False
            eigenvalues.extend(vals)
            flags = _occupation_flags(previous, len(vals))
            occupied_flags.extend(flags)
            current = [[] for _ in vals]
            columns.extend(current)
            previous = line
            continue
        match = _BASIS_LINE.match(line)
        if match is None or current is None:
            previous = line
            continue
        coeffs = _floats(match.group(5))
        if len(coeffs) != len(current):
            continue
        if match.group(2):
            atom_index = int(match.group(2)) - 1
            element = match.group(3) or "?"
        shell = match.group(4)
        for col, value in zip(current, coeffs, strict=True):
            col.append(value)
        if first_block:
            basis.append(
                BasisFn(
                    index=int(match.group(1)),
                    atom_index=atom_index,
                    element=element,
                    shell=shell,
                )
            )
        previous = line

    if not basis or not columns:
        raise ValueError("MO coefficient section did not contain basis functions")
    nbf = len(basis)
    bad = [i for i, col in enumerate(columns) if len(col) != nbf]
    if bad:
        raise ValueError(
            f"MO coefficient columns {bad[:5]} have a different length than the basis ({nbf})"
        )
    coeff = np.column_stack(columns)
    if len(occupied_flags) != coeff.shape[1]:
        occupied_flags = [True] * coeff.shape[1]
    return MoSet(
        basis=basis,
        eigenvalues=np.asarray(eigenvalues, dtype=float),
        coefficients=coeff,
        occupied=np.asarray(occupied_flags, dtype=bool),
        spin="",
    )


def _occupation_flags(previous_line: str, nvals: int) -> list[bool]:
    """Read Gaussian's ``O``/``V`` labels on the line above ``Eigenvalues --``."""
    flags: list[bool] = []
    for tok in previous_line.split():
        upper = tok.upper()
        if upper == "O" or upper.endswith("--O") or upper.endswith("-O"):
            flags.append(True)
        elif upper == "V" or upper.endswith("--V") or upper.endswith("-V"):
            flags.append(False)
    if len(flags) != nvals:
        return [True] * nvals
    return flags


def _section_starts(lines: list[str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if "Molecular Orbital Coefficients" not in line:
            continue
        low = line.lower()
        if "beta" in low:
            kind = "beta"
        elif "alpha" in low:
            kind = "alpha"
        else:
            kind = "restricted"
        found.append((i, kind))
    return found


def _last_s2(text: str) -> float | None:
    matches = list(_S2_RE.finditer(text)) or list(_S2_ALT_RE.finditer(text))
    if not matches:
        return None
    return float(matches[-1].group(1))


def _last_mulliken(lines: list[str]) -> tuple[list[float] | None, list[float] | None]:
    """Return (charges, spin densities) from the last Mulliken block."""
    spin_at: int | None = None
    charge_at: int | None = None
    for i, line in enumerate(lines):
        if _SPIN_HEADER in line:
            spin_at = i
        elif _CHARGE_HEADER in line:
            charge_at = i
    if spin_at is not None:
        charges: list[float] = []
        spins: list[float] = []
        for line in lines[spin_at + 1 :]:
            if line.strip().startswith("Sum of"):
                break
            match = _ATOM_LINE.match(line)
            if match is None:
                continue
            charges.append(float(match.group(3)))
            spins.append(float(match.group(4)))
        if spins:
            return charges, spins
    if charge_at is None:
        return None, None
    charges = []
    for line in lines[charge_at + 1 :]:
        if line.strip().startswith("Sum of"):
            break
        match = _CHARGE_LINE.match(line)
        if match is None:
            continue
        charges.append(float(match.group(3)))
    return (charges or None), None


def parse_population(text: str) -> GaussianPopulation:
    """Parse the last ``pop=full`` MO block plus <S^2> and Mulliken spin."""
    lines = text.splitlines()
    starts = _section_starts(lines)
    pop = GaussianPopulation(s2=_last_s2(text))
    charges, spins = _last_mulliken(lines)
    pop.mulliken_charge = charges
    pop.spin_density = spins
    if not starts:
        return pop

    def _stop(after: int) -> int:
        for j in range(after + 1, len(lines)):
            if "Density Matrix" in lines[j] or (
                "Molecular Orbital Coefficients" in lines[j] and j != after
            ):
                return j
        return len(lines)

    restricted = [i for i, kind in starts if kind == "restricted"]
    alphas = [i for i, kind in starts if kind == "alpha"]
    betas = [i for i, kind in starts if kind == "beta"]
    if alphas and betas and betas[-1] > alphas[-1]:
        alpha = _parse_coefficient_section(lines, alphas[-1], betas[-1])
        alpha.spin = "alpha"
        beta = _parse_coefficient_section(lines, betas[-1], _stop(betas[-1]))
        beta.spin = "beta"
        pop.alpha = alpha
        pop.beta = beta
    elif restricted:
        mos = _parse_coefficient_section(lines, restricted[-1], _stop(restricted[-1]))
        mos.spin = "restricted"
        pop.alpha = mos
    elif alphas:
        alpha = _parse_coefficient_section(lines, alphas[-1], _stop(alphas[-1]))
        alpha.spin = "alpha"
        pop.alpha = alpha
    return pop


def s1_population(coefficients: np.ndarray, basis: list[BasisFn], atom_index: int, mo: int) -> float:
    """Sum of squares of 1S coefficients on ``atom_index`` for one MO column."""
    total = 0.0
    column = coefficients[:, mo]
    for bf, value in zip(basis, column, strict=False):
        if bf.atom_index == atom_index and bf.shell.upper().startswith("1S"):
            total += float(value) * float(value)
    return total


def _atom_masks(basis: list[BasisFn], atom_indices: list[int]) -> list[np.ndarray]:
    masks = []
    for atom in atom_indices:
        mask = np.array(
            [bf.atom_index == atom and bf.shell.upper().startswith("1S") for bf in basis],
            dtype=bool,
        )
        masks.append(mask)
    return masks


def pipek_mezey_1s(
    coefficients: np.ndarray,
    basis: list[BasisFn],
    mo_indices: list[int],
    atom_indices: list[int],
) -> tuple[np.ndarray, float]:
    """Localize ``mo_indices`` (0-based columns) on 1s functions.

    Returns the full coefficient matrix (copy) and the largest |rotation| applied.
    A near-zero rotation means the canonical MOs were already atom-localized.
    """
    coeff = np.array(coefficients, dtype=float, copy=True)
    if len(mo_indices) < 2:
        return coeff, 0.0
    masks = [m for m in _atom_masks(basis, atom_indices) if np.any(m)]
    if len(masks) < 2:
        return coeff, 0.0

    cols = [coeff[:, i] for i in mo_indices]
    work = np.column_stack(cols)
    nmo = work.shape[1]

    def _objective(orbitals: np.ndarray) -> float:
        total = 0.0
        for col in range(orbitals.shape[1]):
            vector = orbitals[:, col]
            for mask in masks:
                pop = float(np.dot(vector[mask], vector[mask]))
                total += pop * pop
        return total

    max_abs = 0.0
    for _sweep in range(80):
        sweep_max = 0.0
        for i in range(nmo):
            for j in range(i + 1, nmo):
                pii = []
                pjj = []
                pij = []
                ci = np.array(work[:, i], copy=True)
                cj = np.array(work[:, j], copy=True)
                for mask in masks:
                    vi = ci[mask]
                    vj = cj[mask]
                    pii.append(float(np.dot(vi, vi)))
                    pjj.append(float(np.dot(vj, vj)))
                    pij.append(float(np.dot(vi, vj)))
                pii_a = np.asarray(pii)
                pjj_a = np.asarray(pjj)
                pij_a = np.asarray(pij)
                # atan2(B, A) / 4 is the Jacobi angle that maximises the
                # Pipek–Mezey objective. A < 0, B = 0 is the delocalized
                # stationary point and must rotate by π/4.
                amat = float(np.sum((pii_a - pjj_a) ** 2 - 4.0 * pij_a**2))
                bmat = float(np.sum(4.0 * pij_a * (pii_a - pjj_a)))
                if abs(amat) < 1e-18 and abs(bmat) < 1e-18:
                    continue
                theta = 0.25 * math.atan2(bmat, amat)
                if abs(theta) < 1e-12:
                    continue
                before = _objective(work)
                cos_t = math.cos(theta)
                sin_t = math.sin(theta)
                new_i = cos_t * ci + sin_t * cj
                new_j = -sin_t * ci + cos_t * cj
                work[:, i] = new_i
                work[:, j] = new_j
                if _objective(work) + 1e-10 < before:
                    work[:, i] = ci
                    work[:, j] = cj
                    theta = -theta
                    cos_t = math.cos(theta)
                    sin_t = math.sin(theta)
                    work[:, i] = cos_t * ci + sin_t * cj
                    work[:, j] = -sin_t * ci + cos_t * cj
                    if _objective(work) + 1e-10 < before:
                        work[:, i] = ci
                        work[:, j] = cj
                        continue
                sweep_max = max(sweep_max, abs(theta))
        max_abs = max(max_abs, sweep_max)
        if sweep_max < 1e-8:
            break
    for local_i, mo in enumerate(mo_indices):
        coeff[:, mo] = work[:, local_i]
    return coeff, max_abs


def _core_mo_indices(eigenvalues: np.ndarray, coefficients: np.ndarray, basis: list[BasisFn]) -> list[int]:
    atoms = sorted({bf.atom_index for bf in basis if bf.shell.upper().startswith("1S")})
    chosen: list[int] = []
    for mo, energy in enumerate(eigenvalues):
        if float(energy) > _CORE_ENERGY_CUTOFF_HA:
            continue
        pop = sum(s1_population(coefficients, basis, atom, mo) for atom in atoms)
        if pop >= 0.25:
            chosen.append(mo)
    return chosen


def _assign_unique(
    scores: dict[int, dict[int, float]],
    *,
    min_pop: float,
) -> dict[int, int]:
    pairs: list[tuple[float, int, int]] = []
    for atom, mos in scores.items():
        for mo, pop in mos.items():
            pairs.append((pop, atom, mo))
    pairs.sort(reverse=True)
    used_atoms: set[int] = set()
    used_mos: set[int] = set()
    assignment: dict[int, int] = {}
    for pop, atom, mo in pairs:
        if atom in used_atoms or mo in used_mos:
            continue
        if pop < min_pop:
            continue
        assignment[atom] = mo
        used_atoms.add(atom)
        used_mos.add(mo)
    return assignment


def _element_of_mo(coefficients: np.ndarray, basis: list[BasisFn], mo: int, atoms: list[int]) -> str | None:
    best_atom = None
    best_pop = -1.0
    for atom in atoms:
        pop = s1_population(coefficients, basis, atom, mo)
        if pop > best_pop:
            best_pop = pop
            best_atom = atom
    if best_atom is None or best_pop < 0.05:
        return None
    for bf in basis:
        if bf.atom_index == best_atom:
            return bf.element
    return None


def resolve_core_orbitals(
    orbitals: list[Orbital],
    xps_atoms: list[tuple[int, str]],
    population: GaussianPopulation | None = None,
) -> CoreOrbitalMap:
    """Map each C/N/O atom to its 1s MO.

    With ``pop=full`` coefficients the map follows 1s populations, after
    localizing delocalized core subspaces. Without coefficients, MOs are
    matched to elements by eigenvalue window (never across elements).
    """
    if population is not None and population.alpha is not None:
        return _resolve_from_coefficients(orbitals, xps_atoms, population.alpha)
    by_atom = _assign_by_element_window(orbitals, xps_atoms)
    return CoreOrbitalMap(
        by_atom=by_atom,
        population={},
        guess_style="alter",
        coefficients=None,
        warnings=[
            "Neutral log has no MO coefficients (pop=full). "
            "1s orbitals were matched to elements by eigenvalue window only; "
            "which atom within an element gets which MO is not known, and "
            "delocalized canonical orbitals are not localized."
        ],
    )


def _assign_by_element_window(
    orbitals: list[Orbital],
    xps_atoms: list[tuple[int, str]],
) -> dict[int, int]:
    occupied = [o for o in orbitals if o.occupancy > 0.1]
    used: set[int] = set()
    result: dict[int, int] = {}
    for element in ("O", "N", "C"):
        atoms = [idx for idx, el in xps_atoms if el == element]
        if not atoms:
            continue
        lo, hi = CORE_WINDOWS_HA[element]
        cand = [
            o
            for o in occupied
            if lo <= o.energy_ha <= hi and o.index not in used
        ]
        cand.sort(key=lambda o: o.energy_ha)
        if len(cand) < len(atoms):
            raise ValueError(
                f"Expected {len(atoms)} {element} 1s orbitals in {lo:.1f}…{hi:.1f} Ha, "
                f"found {len(cand)}. Re-run the neutral SP with pop=full so 1s "
                "orbitals can be assigned from MO coefficients."
            )
        for atom, orb in zip(atoms, cand, strict=True):
            result[atom] = orb.index
            used.add(orb.index)
    missing = [idx for idx, _el in xps_atoms if idx not in result]
    if missing:
        raise ValueError(f"No 1s orbital assigned for atoms {missing}")
    return result


def _resolve_from_coefficients(
    orbitals: list[Orbital],
    xps_atoms: list[tuple[int, str]],
    mos: MoSet,
) -> CoreOrbitalMap:
    coeff = mos.coefficients
    basis = mos.basis
    evals = mos.eigenvalues
    xps_index = {idx: el for idx, el in xps_atoms}
    core_mos = _core_mo_indices(evals, coeff, basis)
    if len(core_mos) < len(xps_atoms):
        raise ValueError(
            f"Found {len(core_mos)} core-like MOs for {len(xps_atoms)} C/N/O atoms"
        )

    by_element: dict[str, list[int]] = {}
    for mo in core_mos:
        element = _element_of_mo(coeff, basis, mo, list(xps_index))
        if element is None:
            continue
        by_element.setdefault(element, []).append(mo)

    localized = coeff
    max_rotation = 0.0
    for element, mo_list in by_element.items():
        atoms = [idx for idx, el in xps_atoms if el == element]
        localized, rotated = pipek_mezey_1s(localized, basis, mo_list, atoms)
        max_rotation = max(max_rotation, rotated)

    scores: dict[int, dict[int, float]] = {}
    candidate_mos = [mo for mos_el in by_element.values() for mo in mos_el]
    for atom, element in xps_atoms:
        scores[atom] = {
            mo: s1_population(localized, basis, atom, mo) for mo in candidate_mos
        }
    assigned = _assign_unique(scores, min_pop=_MIN_POP)
    missing = [idx for idx, _el in xps_atoms if idx not in assigned]
    if missing:
        detail = []
        for atom in missing:
            best = max(scores.get(atom, {}).items(), key=lambda kv: kv[1], default=(None, 0.0))
            detail.append(f"atom {atom + 1} best 1s population {best[1]:.3f} on MO {best[0]}")
        raise ValueError(
            "Could not assign a localized 1s orbital to every C/N/O atom: " + "; ".join(detail)
        )

    populations = {atom: scores[atom][mo] for atom, mo in assigned.items()}
    # Reject an assignment whose largest 1s weight is on the wrong element.
    for atom, mo in assigned.items():
        owner = _element_of_mo(localized, basis, mo, list(xps_index))
        if owner is not None and owner != xps_index[atom]:
            raise ValueError(
                f"Atom {atom + 1} ({xps_index[atom]}) was assigned an {owner} 1s MO"
            )

    needs_cards = max_rotation > 1e-3 or any(pop < _LOCALIZED_POP for pop in populations.values())
    # Column indices are 0-based; Gaussian MO numbers are 1-based.
    by_atom = {atom: mo + 1 for atom, mo in assigned.items()}
    warnings: list[str] = []
    if needs_cards:
        warnings.append(
            "Canonical 1s MOs are delocalized over symmetry-equivalent atoms. "
            "Core-hole steps use Guess=Cards with Pipek–Mezey localized 1s orbitals "
            "so the hole is on one atom."
        )
    return CoreOrbitalMap(
        by_atom=by_atom,
        population=populations,
        guess_style="cards" if needs_cards else "alter",
        coefficients=localized if needs_cards else None,
        eigenvalues=evals,
        warnings=warnings,
    )


def fortran_e20_8(value: float) -> str:
    """One Fortran ``E20.8`` field (``0.ddddddddE±ee``), width 20.

    This is the format Gaussian's ``Guess=Cards`` example reads.
    """
    if not math.isfinite(value):
        raise ValueError(f"Non-finite MO coefficient: {value}")
    sign = "-" if value < 0 else " "
    mag = abs(value)
    if mag == 0.0:
        body = f"{sign}0.00000000E+00"
        return body.rjust(20)
    exp = int(math.floor(math.log10(mag))) + 1
    mant = mag / (10**exp)
    # Keep the mantissa in [0.1, 1) except for exact powers of ten.
    if mant >= 1.0:
        mant /= 10.0
        exp += 1
    if mant < 0.1:
        mant *= 10.0
        exp -= 1
    body = f"{sign}{mant:.8f}E{exp:+03d}"
    if len(body) > 20:
        raise ValueError(f"Coefficient {value} does not fit E20.8 ({body})")
    return body.rjust(20)


def _coefficients_block(matrix: np.ndarray) -> list[str]:
    """MO columns, 4 coefficients per line, each ``E20.8``."""
    nbf, nmo = matrix.shape
    lines: list[str] = []
    for mo in range(nmo):
        lines.append(f"{mo + 1:5d}")
        column = matrix[:, mo]
        for start in range(0, nbf, 4):
            chunk = column[start : start + 4]
            lines.append("".join(fortran_e20_8(float(v)) for v in chunk))
    return lines


def format_guess_cards(alpha: np.ndarray, beta: np.ndarray) -> str:
    """``Guess=Cards`` replacement for a UKS initial guess.

    Gaussian reads a Fortran format line, then alpha orbitals (I5 index,
    coefficients, ``0`` to end). The beta section repeats without a second
    format line. See Gaussian 09 ``Guess=Cards``.
    """
    if alpha.shape != beta.shape:
        raise ValueError(f"Alpha/beta shapes differ: {alpha.shape} vs {beta.shape}")
    lines = ["(4E20.8)", *_coefficients_block(alpha), f"{0:5d}", *_coefficients_block(beta), f"{0:5d}"]
    return "\n".join(lines) + "\n"


def beta_with_core_hole(alpha: np.ndarray, core_mo: int, vacancy_mo: int) -> np.ndarray:
    """Copy alpha orbitals and swap the localized 1s into the β vacancy slot.

    For a closed-shell neutral, ``Guess=Read`` on the cation leaves β MO
    ``n_occ`` empty. Swapping that slot with the target 1s puts the hole on
    the localized core orbital (same convention as ``Guess=Alter``).
    """
    if core_mo < 1 or vacancy_mo < 1:
        raise ValueError(f"Invalid MO pair core={core_mo}, vacancy={vacancy_mo}")
    nmo = alpha.shape[1]
    if core_mo > nmo or vacancy_mo > nmo:
        raise ValueError(f"MO pair ({core_mo}, {vacancy_mo}) outside 1…{nmo}")
    if core_mo == vacancy_mo:
        raise ValueError("Core and vacancy MO are the same")
    beta = np.array(alpha, dtype=float, copy=True)
    i = core_mo - 1
    j = vacancy_mo - 1
    core = beta[:, i].copy()
    beta[:, i] = beta[:, j]
    beta[:, j] = core
    return beta


def be_in_window(element: str, be_ev: float) -> bool:
    window = BE_WINDOWS_EV.get(element)
    if window is None:
        return be_ev > 50.0
    lo, hi = window
    return lo <= be_ev <= hi


def assess_core_hole(
    *,
    element: str,
    atom_index: int,
    multiplicity: int,
    be_raw_ev: float | None,
    population: GaussianPopulation | None,
) -> CoreHoleVerdict:
    """Reject a core-hole SCF that collapsed or landed on the wrong atom.

    Checks, when the log contains the data (``pop=full`` + UKS):

    * ``<S**2>`` near 0.75 for a doublet (0 for a singlet)
    * Mulliken spin density on the target atom near ±1 for a doublet
    * 1s population filled in alpha and empty in beta on that atom
    * raw BE inside the element 1s window
    """
    failures: list[str] = []
    warnings: list[str] = []
    s2 = population.s2 if population else None
    spin = None
    if population and population.spin_density is not None and 0 <= atom_index < len(population.spin_density):
        spin = population.spin_density[atom_index]

    expected_s2 = 0.75 if int(multiplicity) == 2 else 0.0
    tol_s2 = 0.25 if int(multiplicity) == 2 else 0.15
    if s2 is None:
        warnings.append("<S^2> was not found in the core-hole log")
    elif abs(s2 - expected_s2) > tol_s2:
        failures.append(
            f"<S^2>={s2:.3f} (expected ~{expected_s2:.2f} for multiplicity {multiplicity})"
        )

    if int(multiplicity) == 2:
        if spin is None:
            warnings.append("Mulliken spin density was not found (need pop=full)")
        elif abs(spin) < 0.50:
            failures.append(
                f"Mulliken spin density on {element}{atom_index + 1} is {spin:.3f} "
                "(expected |spin|≈1 for a 1s hole on that atom)"
            )
    elif spin is not None and abs(spin) > 0.40:
        warnings.append(
            f"Singlet core-hole has spin density {spin:.3f} on {element}{atom_index + 1}"
        )

    alpha_pop = None
    beta_pop = None
    if population and population.alpha is not None:
        alpha_pop = _best_occupied_1s(population.alpha, atom_index, occupied=True)
        if population.beta is not None:
            beta_pop = _best_occupied_1s(population.beta, atom_index, occupied=True)
        else:
            # Restricted print, or UKS log whose beta block was not written.
            beta_pop = None
        if alpha_pop is None:
            warnings.append("Could not read a 1s population on the target atom")
        else:
            if alpha_pop < 0.40:
                failures.append(
                    f"Alpha 1s population on {element}{atom_index + 1} is {alpha_pop:.2f} "
                    "(expected a filled 1s, ~1)"
                )
            if beta_pop is not None and beta_pop > 0.40:
                failures.append(
                    f"Beta 1s population on {element}{atom_index + 1} is {beta_pop:.2f} "
                    "(expected a core hole, ~0). The hole likely collapsed to the valence."
                )
            if beta_pop is None:
                warnings.append("Beta MO coefficients were not found; 1s occupation was checked on alpha only")
    else:
        warnings.append("MO coefficients were not found; 1s occupation was not checked")

    if be_raw_ev is None:
        warnings.append("Binding energy could not be computed")
    elif not be_in_window(element, be_raw_ev):
        lo, hi = BE_WINDOWS_EV.get(element, (50.0, 1000.0))
        failures.append(
            f"Raw BE {be_raw_ev:.1f} eV is outside the {element}1s window {lo:.0f}–{hi:.0f} eV"
        )

    if not failures and warnings and alpha_pop is None and spin is None and s2 is None:
        warnings.append("Core-hole log has no population data; only the BE window was available")

    return CoreHoleVerdict(
        ok=not failures,
        failures=failures,
        warnings=warnings,
        s2=s2,
        spin_density=spin,
        alpha_1s_population=alpha_pop,
        beta_1s_population=beta_pop,
    )


def _best_occupied_1s(mos: MoSet, atom_index: int, *, occupied: bool) -> float | None:
    """Largest 1s population on ``atom_index`` among occupied core-energy MOs.

    An empty core orbital can still have a very negative eigenvalue, so the
    ``O``/``V`` label (not the eigenvalue alone) decides occupation.
    """
    if mos.coefficients.size == 0:
        return None
    best = 0.0
    nmo = mos.coefficients.shape[1]
    for mo in range(nmo):
        if occupied and mo < len(mos.occupied) and not bool(mos.occupied[mo]):
            continue
        energy = float(mos.eigenvalues[mo]) if mo < len(mos.eigenvalues) else 0.0
        if energy > _CORE_ENERGY_CUTOFF_HA:
            continue
        best = max(best, s1_population(mos.coefficients, mos.basis, atom_index, mo))
    return best
