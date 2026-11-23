"""L2 — ΔSCF XPS workflow (gas-phase, Gaussian 09).

Protocol: OPT → neutral SP (E₀) → core-hole SP per C/N/O atom (Eᵢ).
Binding energy: BEᵢ = (Eᵢ − E₀) × 27.211386 eV; optional C1s alignment shift.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.core.models import CoreLevel, Orbital

HA_TO_EV = 27.211386245988
REF_C1S_EV = 284.3


class StepKind(str, Enum):
    OPT = "opt"
    NEUTRAL_SP = "neutral_sp"
    COREHOLE_SP = "corehole_sp"


class StepStatus(str, Enum):
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DscfStep:
    key: str
    kind: StepKind
    title: str
    user_hint: str
    status: StepStatus = StepStatus.WAITING
    route: str = ""
    gjf_name: str = ""
    log_name: str = ""
    energy_ha: float | None = None
    atom_index: int | None = None
    element: str | None = None
    orbital_index: int | None = None  # 1s MO to ionize (1-based)
    homo_index: int | None = None  # β vacancy MO after Guess=Read (= n_occ)
    error: str = ""
    guess_style: str = "alter"  # alter | cards
    weight: int = 1
    energy_ev: float | None = None  # GPAW totals are eV, not Hartree
    diagnostics: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DscfStep:
        return cls(
            key=raw["key"],
            kind=StepKind(raw["kind"]),
            title=raw["title"],
            user_hint=raw["user_hint"],
            status=StepStatus(raw.get("status", StepStatus.WAITING.value)),
            route=raw.get("route", ""),
            gjf_name=raw.get("gjf_name", ""),
            log_name=raw.get("log_name", ""),
            energy_ha=raw.get("energy_ha"),
            atom_index=raw.get("atom_index"),
            element=raw.get("element"),
            orbital_index=raw.get("orbital_index"),
            homo_index=raw.get("homo_index"),
            error=raw.get("error", ""),
            guess_style=raw.get("guess_style", "alter"),
            weight=int(raw.get("weight", 1) or 1),
            energy_ev=raw.get("energy_ev"),
            diagnostics=raw.get("diagnostics", ""),
        )


@dataclass
class DscfSettings:
    functional: str = "pbe"
    basis: str = "6-31g(d)"
    fwhm_ev: float = 1.2
    c1s_ref_ev: float = REF_C1S_EV
    n1s_ref_ev: float = 399.3
    o1s_ref_ev: float = 530.6
    apply_c1s_shift: bool = True
    reference_mode: str = "absolute"
    reference_element: str = "C"


# Gaussian 09 method names (UI may store short aliases like "pbe").
_FUNCTIONAL_G09 = {
    "pbe": "PBEPBE",
    "pbepbe": "PBEPBE",
    "b3lyp": "B3LYP",
}


def gaussian_method(functional: str) -> str:
    """Map Settings functional alias to a G09 DFT keyword."""
    key = (functional or "pbe").strip().lower()
    return _FUNCTIONAL_G09.get(key, (functional or "PBEPBE").strip().upper())


def gaussian_method_unrestricted(functional: str) -> str:
    """Unrestricted DFT: ``UPBEPBE``, ``UB3LYP``, … (not a separate ``uks`` keyword)."""
    method = gaussian_method(functional)
    return method if method.upper().startswith("U") else f"U{method}"


def _integral_keyword() -> str:
    # Prefer full Integral= form — bare "int=" is ambiguous in G09 (QPErr).
    return "Integral=UltraFine"


def opt_route(settings: DscfSettings) -> str:
    method = gaussian_method(settings.functional)
    return f"opt {method}/{settings.basis} geom=connectivity {_integral_keyword()}"


def neutral_route(settings: DscfSettings) -> str:
    """Neutral SP. Omit Integral here so the ``#`` line stays under G09's ~70-char limit."""
    method = gaussian_method(settings.functional)
    return f"sp {method}/{settings.basis} pop=full geom=checkpoint guess=read"


def corehole_route(settings: DscfSettings, *, cards: bool = False) -> str:
    """Core-hole UKS SP.

    Use ``UPBEPBE`` (not ``uks PBEPBE``). ``SCF=XQC`` switches to quadratic
    convergence when DIIS stalls. ``pop=full`` is required so the log can be
    checked for 1s occupation, Mulliken spin, and ``<S**2>``. ``nosymm`` keeps
    Gaussian from re-symmetrizing a localized hole. The route is wrapped on
    spaces into ``#`` lines of at most 70 characters.
    """
    method = gaussian_method_unrestricted(settings.functional)
    guess = "guess=(read,cards)" if cards else "guess=(read,alter)"
    return (
        f"{method}/{settings.basis} geom=check "
        f"{guess} nosymm pop=full SCF=(XQC,MaxCyc=512)"
    )


def corehole_charge_multiplicity(
    neutral_charge: int,
    neutral_multiplicity: int,
) -> tuple[int, int]:
    """Charge/mult for the core-ionized state (ΔSCF CEBE).

    XPS ΔSCF removes one electron: ``charge = neutral_charge + 1``.
    That flips electron-count parity, so a closed-shell singlet (mult 1) becomes
    a doublet cation (mult 2). A doublet radical becomes a singlet cation.
    Using mult 2 with an even electron count (e.g. neutral ethane, 18 e⁻) makes
    Gaussian abort: \"multiplicity 2 and 18 electrons is impossible\".
    """
    charge = int(neutral_charge) + 1
    nmult = int(neutral_multiplicity) if neutral_multiplicity else 1
    if nmult == 1:
        multiplicity = 2
    elif nmult == 2:
        multiplicity = 1
    else:
        multiplicity = max(1, nmult - 1)
    return charge, multiplicity


def list_xps_atoms(atoms: list[tuple[str, float, float, float]]) -> list[tuple[int, str]]:
    """Return (0-based atom index, element) for C/N/O in input order."""
    out: list[tuple[int, str]] = []
    for idx, (sym, *_rest) in enumerate(atoms):
        if sym in ("C", "N", "O"):
            out.append((idx, sym))
    return out


def build_workflow_steps(
    atoms: list[tuple[str, float, float, float]],
    settings: DscfSettings,
    job_id: int,
) -> list[DscfStep]:
    """Plan OPT → neutral SP → one core-hole SP per heavy atom."""
    xps_atoms = list_xps_atoms(atoms)
    steps: list[DscfStep] = [
        DscfStep(
            key="opt",
            kind=StepKind.OPT,
            title="Step 1 · Geometry optimization",
            user_hint=(
                "Optimizes 3D geometry in the gas phase. "
                "Uses your charge and multiplicity from Compounds. "
                "Produces a checkpoint for all later single-points."
            ),
            status=StepStatus.QUEUED,
            route=opt_route(settings),
            gjf_name=f"job_{job_id}_01_opt.gjf",
            log_name=f"job_{job_id}_01_opt.log",
        ),
        DscfStep(
            key="neutral_sp",
            kind=StepKind.NEUTRAL_SP,
            title="Step 2 · Neutral ground-state SP",
            user_hint=(
                "Single-point at the OPT geometry with pop=full. "
                "Records E₀ and maps each atom's 1s orbital for core-hole jobs. "
                "Requires Step 1 checkpoint."
            ),
            status=StepStatus.WAITING,
            route=neutral_route(settings),
            gjf_name=f"job_{job_id}_02_neutral.gjf",
            log_name=f"job_{job_id}_02_neutral.log",
        ),
    ]
    for n, (atom_idx, element) in enumerate(xps_atoms, start=1):
        label = f"{element}{atom_idx + 1}"
        steps.append(
            DscfStep(
                key=f"corehole_{atom_idx}",
                kind=StepKind.COREHOLE_SP,
                title=f"Step {2 + n} · Core hole on {label}",
                user_hint=(
                    f"UKS single-point: core-ionized (+1) with a 1s hole on atom "
                    f"{atom_idx + 1} ({element}). Guess=Alter swaps that 1s with the "
                    f"vacant β MO (former HOMO / n_occ), not a valence occupied MO. "
                    f"BE = E(cation, core hole) − E₀. Requires Step 2."
                ),
                status=StepStatus.WAITING,
                route=corehole_route(settings),
                gjf_name=f"job_{job_id}_corehole_{label}.gjf",
                log_name=f"job_{job_id}_corehole_{label}.log",
                atom_index=atom_idx,
                element=element,
            )
        )
    return steps


def assign_core_orbitals(
    orbitals: list[Orbital],
    xps_atoms: list[tuple[int, str]],
    population: Any = None,
) -> dict[int, int]:
    """Map atom index → 1s orbital number (1-based).

    With ``pop=full`` coefficients each atom gets the 1s MO localized on that
    atom. Without coefficients, MOs are matched by element eigenvalue window
    (an N 1s is never given to carbon). The old energy-sorted, input-order
    pairing is not used: on melamine it assigned C1 the N 1s at about −14.3 Ha.
    """
    from src.core.gaussian_mos import resolve_core_orbitals

    return resolve_core_orbitals(orbitals, xps_atoms, population).by_atom


def homo_orbital_index(orbitals: list[Orbital]) -> int:
    occupied = [o for o in orbitals if o.occupancy > 0.1]
    if not occupied:
        raise ValueError("No occupied orbitals in neutral SP log")
    return max(occupied, key=lambda o: o.energy_ha).index


def corehole_vacancy_index(orbitals: list[Orbital]) -> int:
    """MO index that must be vacant in the β set of the doublet cation.

    Closed-shell neutral with N doubly occupied MOs → remove one β electron →
    default Guess=Read leaves the vacancy on MO **N** (former HOMO / first virtual
    in the β set). Guess=Alter must swap the target **occupied 1s** with this
    **virtual** index. Swapping two occupied MOs does nothing to the vacancy, so
    the hole stays valence (outer shell).
    """
    occupied = [o for o in orbitals if o.occupancy > 0.1]
    if not occupied:
        raise ValueError("No occupied orbitals in neutral SP log")
    return len(occupied)


def corehole_alter_pair(core_mo: int, vacancy_mo: int) -> tuple[int, int]:
    """Validate and return (core, vacancy) for β Guess=Alter."""
    if core_mo < 1 or vacancy_mo < 1:
        raise ValueError(f"Invalid Alter pair: core={core_mo}, vacancy={vacancy_mo}")
    if core_mo >= vacancy_mo:
        raise ValueError(
            f"Core MO {core_mo} must be below vacancy MO {vacancy_mo} "
            "(vacancy = former HOMO / first virtual in the cation β set)"
        )
    return core_mo, vacancy_mo


def compute_binding_energies(
    e0_ha: float,
    corehole_energies: list[tuple[int, str, float]],
    c1s_ref_ev: float = REF_C1S_EV,
    apply_c1s_shift: bool = True,
    *,
    reference_mode: str | None = None,
    reference_element: str = "C",
    n1s_ref_ev: float = 399.3,
    o1s_ref_ev: float = 530.6,
    weights: dict[int, float] | None = None,
    info: dict[str, Any] | None = None,
) -> list[CoreLevel]:
    """Build CoreLevel rows from ΔSCF total energies (Ha → eV).

    ``reference_mode`` selects absolute, one global calibration shift, or a
    per-element shift. When it is omitted, ``apply_c1s_shift=True`` keeps the
    previous global C1s calibration and ``False`` leaves the raw ΔSCF values.
    """
    from src.core.referencing import apply_be_reference, element_references

    levels: list[CoreLevel] = []
    for atom_index, element, e_ha in corehole_energies:
        be_raw = (e_ha - e0_ha) * HA_TO_EV
        levels.append(
            CoreLevel(
                element=element,
                atom_index=atom_index,
                orbital_index=0,
                energy_ha=e_ha - e0_ha,
                binding_ev_raw=be_raw,
                binding_ev_scaled=be_raw,
                binding_ev_shifted=be_raw,
                binding_ev_final=be_raw,
                weight=float((weights or {}).get(atom_index, 1.0)),
            )
        )

    if reference_mode is None:
        reference_mode = "global" if apply_c1s_shift else "absolute"
    meta = apply_be_reference(
        levels,
        reference_mode,
        refs=element_references(c1s=c1s_ref_ev, n1s=n1s_ref_ev, o1s=o1s_ref_ev),
        reference_element=reference_element,
    )
    if info is not None:
        info.update(meta)
    return levels


def workflow_progress(steps: list[DscfStep]) -> float:
    if not steps:
        return 0.0
    done = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
    return done / len(steps)


def next_runnable_step(steps: list[DscfStep]) -> DscfStep | None:
    for step in steps:
        if step.status == StepStatus.QUEUED:
            return step
        if step.status == StepStatus.RUNNING:
            return step
    return None


def is_dscf_workflow(steps: list[DscfStep]) -> bool:
    """True when steps include the neutral SP required for ΔSCF curation."""
    return bool(steps) and any(s.kind == StepKind.NEUTRAL_SP for s in steps)


def serialize_steps(steps: list[DscfStep]) -> list[dict[str, Any]]:
    return [s.to_dict() for s in steps]


def deserialize_steps(raw: list[dict[str, Any]]) -> list[DscfStep]:
    return [DscfStep.from_dict(item) for item in raw]
