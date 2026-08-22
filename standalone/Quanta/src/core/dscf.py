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
    orbital_index: int | None = None
    homo_index: int | None = None
    error: str = ""

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
        )


@dataclass
class DscfSettings:
    functional: str = "pbe"
    basis: str = "6-31g(d)"
    fwhm_ev: float = 1.2
    c1s_ref_ev: float = REF_C1S_EV
    apply_c1s_shift: bool = True


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


def corehole_route(settings: DscfSettings) -> str:
    """Core-hole UKS SP.

    Use ``UPBEPBE`` (not ``uks PBEPBE``). One short ``#`` line — G09 hard-wraps
    longer route cards mid-token (``guess`` → ``g`` / ``uess``) and QPErr.
    """
    method = gaussian_method_unrestricted(settings.functional)
    return f"{method}/{settings.basis} pop=full geom=checkpoint guess=(read,alter)"


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
                    f"{atom_idx + 1} ({element}). Guess=Alter swaps that 1s with HOMO. "
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
) -> dict[int, int]:
    """Map atom index → 1s orbital number (1-based, from neutral SP)."""
    occupied = sorted(
        [o for o in orbitals if o.occupancy > 0.1],
        key=lambda o: o.energy_ha,
    )
    n_core = len(xps_atoms)
    if len(occupied) < n_core:
        raise ValueError(
            f"Expected at least {n_core} occupied core orbitals, found {len(occupied)}"
        )
    core_orbs = occupied[:n_core]
    return {atom_idx: core_orbs[i].index for i, (atom_idx, _el) in enumerate(xps_atoms)}


def homo_orbital_index(orbitals: list[Orbital]) -> int:
    occupied = [o for o in orbitals if o.occupancy > 0.1]
    if not occupied:
        raise ValueError("No occupied orbitals in neutral SP log")
    return max(occupied, key=lambda o: o.energy_ha).index


def compute_binding_energies(
    e0_ha: float,
    corehole_energies: list[tuple[int, str, float]],
    c1s_ref_ev: float = REF_C1S_EV,
    apply_c1s_shift: bool = True,
) -> list[CoreLevel]:
    """Build CoreLevel rows from ΔSCF total energies (Ha → eV)."""
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
            )
        )

    if apply_c1s_shift:
        c_vals = [lv.binding_ev_raw for lv in levels if lv.element == "C"]
        if c_vals:
            shift = c1s_ref_ev - (sum(c_vals) / len(c_vals))
            for lv in levels:
                lv.binding_ev_shifted = lv.binding_ev_raw + shift
                lv.binding_ev_final = lv.binding_ev_shifted
        else:
            for lv in levels:
                lv.binding_ev_final = lv.binding_ev_raw
    else:
        for lv in levels:
            lv.binding_ev_final = lv.binding_ev_raw
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
