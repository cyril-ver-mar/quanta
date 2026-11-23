"""Periodic ΔSCF XPS with ASE + GPAW (no GPAW import in this module).

Method
------
Full 1s core-hole PAW dataset, then one SCF per symmetry-inequivalent site
in a supercell. This follows the GPAW ΔKohn–Sham recipe in the XAS tutorial
(``gpaw-setup --core-hole`` dataset, ``get_potential_energy() +
get_reference_energy()``) and the neutral supercell used by Susi et al.,
Phys. Rev. B 91, 081401 (2015), for graphene C1s.

Electron count
--------------
``gpaw-setup ELEMENT --name fch1s --core-hole=1s,1.0`` builds a dataset with
one fewer core electron and the same valence count as the ground-state setup.

* **neutral** (default): ``charge=-1`` together with that dataset puts the
  core electron into the valence. The cell stays neutral; the extra electron
  sits in the conduction band. Calculator arguments match the GPAW ΔKS
  example: ``spinpol=True``, magnetic moment 1 on the excited atom,
  ``occupations=FermiDirac(width, fixmagmom=True)``.
* **charged**: ``charge=0`` with the same dataset removes the core electron
  and does not put it back. Under periodic boundary conditions GPAW adds a
  neutralizing background, so the raw ΔE is not vacuum-aligned.

Binding energies
----------------
``BE_raw = E_core − E_ground``, both totals including ``get_reference_energy()``.
Energies are eV, as GPAW reports them.

* ``absolute``: ``BE_raw``.
* ``fermi``: neutral mode already places the photoelectron at the band edge,
  so ``BE_raw`` is the Fermi-referenced value for a metal (Susi). Charged
  mode reports ``BE_raw − ε_F`` of the ground state, with the background-charge
  caveat.
* ``vbm``: neutral mode adds the ground-state gap, ``BE_raw + (ε_CBM − ε_VBM)``,
  an estimate of the BE relative to the VBM when the extra electron sits at
  the CBM. Charged mode reports ``BE_raw − ε_VBM``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.dscf import DscfStep, StepKind, StepStatus
from src.core.models import CoreLevel
from src.core.periodic import (
    CrystalSite,
    PeriodicStructure,
    inequivalent_sites,
    make_supercell,
    parse_int_triple,
)
from src.core.referencing import apply_be_reference, element_references

HA_NOTE = (
    "GPAW total energies are in eV. They are not stored as Hartree."
)

# Charge of the core-hole calculation relative to a neutral ground state,
# for one full 1s core-hole dataset. See the module docstring.
CHARGE_NEUTRAL = -1
CHARGE_CHARGED = 0


@dataclass
class GpawSettings:
    xc: str = "PBE"
    pw_cutoff_ev: float = 500.0
    kpts: tuple[int, int, int] = (1, 1, 1)
    supercell: tuple[int, int, int] = (1, 1, 1)
    charge_mode: str = "neutral"  # neutral | charged
    smearing_ev: float = 0.1
    setup_name: str = "fch1s"
    setup_dir: str = ""
    elements: tuple[str, ...] = ("C", "N")
    reference_mode: str = "absolute"
    reference_element: str = "C"
    c1s_ref_ev: float = 284.3
    n1s_ref_ev: float = 399.3
    o1s_ref_ev: float = 530.6
    fwhm_ev: float = 1.2
    base_charge: int = 0
    symprec: float = 1e-3

    @classmethod
    def from_app(cls, settings: Any, *, base_charge: int = 0) -> GpawSettings:
        elements = tuple(
            part.strip()
            for part in str(getattr(settings, "gpaw_elements", "C,N")).split(",")
            if part.strip()
        ) or ("C", "N")
        return cls(
            xc=str(getattr(settings, "gpaw_xc", "PBE") or "PBE"),
            pw_cutoff_ev=float(getattr(settings, "gpaw_pw_cutoff_ev", 500.0)),
            kpts=parse_int_triple(str(getattr(settings, "gpaw_kpts", "1,1,1")), name="k-points"),
            supercell=parse_int_triple(
                str(getattr(settings, "gpaw_supercell", "1,1,1")), name="supercell"
            ),
            charge_mode=str(getattr(settings, "gpaw_charge_mode", "neutral") or "neutral"),
            smearing_ev=float(getattr(settings, "gpaw_smearing_ev", 0.1)),
            setup_name=str(getattr(settings, "gpaw_setup_name", "fch1s") or "fch1s"),
            setup_dir=str(getattr(settings, "gpaw_setup_dir", "") or ""),
            elements=elements,  # type: ignore[arg-type]
            reference_mode=str(getattr(settings, "xps_reference_mode", "absolute") or "absolute"),
            reference_element=str(getattr(settings, "xps_reference_element", "C") or "C"),
            c1s_ref_ev=float(getattr(settings, "xps_c1s_ref_ev", 284.3)),
            n1s_ref_ev=float(getattr(settings, "xps_n1s_ref_ev", 399.3)),
            o1s_ref_ev=float(getattr(settings, "xps_o1s_ref_ev", 530.6)),
            fwhm_ev=float(getattr(settings, "xps_fwhm_ev", 1.2)),
            base_charge=int(base_charge),
        )


def gpaw_available() -> tuple[bool, str]:
    """Lazy import. GPAW is optional; Gaussian jobs do not need it."""
    try:
        import gpaw  # noqa: F401
        from gpaw import GPAW, PW, FermiDirac  # noqa: F401
    except ImportError as exc:
        return (
            False,
            "GPAW is not installed, so periodic XPS cannot run. "
            "Install it from conda-forge (`conda install -c conda-forge gpaw`) "
            "and generate full 1s core-hole setups, for example "
            "`gpaw-setup -f PBE C --name fch1s --core-hole=1s,1.0` "
            "(same for N and O). Put the datasets on GPAW_SETUP_PATH or set "
            "the setup directory in Settings. "
            f"Import error: {exc}",
        )
    return True, ""


def charge_for_mode(charge_mode: str, base_charge: int = 0) -> int:
    """GPAW ``charge`` for one full 1s core-hole dataset.

    ``neutral`` → ``base_charge - 1`` (extra valence electron).
    ``charged`` → ``base_charge`` (core electron removed, no extra valence electron).
    """
    mode = (charge_mode or "neutral").strip().lower()
    if mode == "neutral":
        return int(base_charge) + CHARGE_NEUTRAL
    if mode == "charged":
        return int(base_charge) + CHARGE_CHARGED
    raise ValueError("charge_mode must be 'neutral' or 'charged'")


def calculator_keywords(
    settings: GpawSettings,
    *,
    kind: str,
    atom_index: int | None,
    txt: str,
) -> dict[str, Any]:
    """Keyword arguments for ``gpaw.GPAW``, using documented parameters only.

    The runner turns ``mode`` into ``PW(cutoff)`` and ``occupations`` into
    ``FermiDirac``. Names match the GPAW ΔKS example and the GPAW parameter
    list (``mode``, ``xc``, ``kpts``, ``txt``, ``charge``, ``spinpol``,
    ``setups``, ``occupations``, ``symmetry``).
    """
    if settings.pw_cutoff_ev <= 0:
        raise ValueError("Plane-wave cutoff must be positive (eV)")
    keywords: dict[str, Any] = {
        "mode": {"type": "pw", "cutoff_ev": float(settings.pw_cutoff_ev)},
        "xc": settings.xc,
        "kpts": tuple(settings.kpts),
        "txt": txt,
        "charge": int(settings.base_charge) if kind == "neutral" else charge_for_mode(
            settings.charge_mode, settings.base_charge
        ),
        "occupations": {
            "name": "fermi-dirac",
            "width_ev": float(settings.smearing_ev),
            "fixmagmom": kind == "corehole" and settings.charge_mode == "neutral",
        },
    }
    if kind == "corehole":
        if atom_index is None:
            raise ValueError("Core-hole calculation needs an atom index")
        keywords["spinpol"] = True
        keywords["setups"] = {int(atom_index): settings.setup_name}
        # Do not replicate the core hole onto symmetry copies.
        keywords["symmetry"] = {"point_group": False, "time_reversal": False}
        if settings.charge_mode == "neutral":
            keywords["magmom_atom"] = int(atom_index)
            keywords["magmom"] = 1.0
    return keywords


def plan_gpaw_steps(
    structure: PeriodicStructure,
    settings: GpawSettings,
    job_id: int,
) -> tuple[list[DscfStep], list[CrystalSite]]:
    """Neutral ground state, then one core hole per inequivalent C/N (or chosen) site."""
    sites = inequivalent_sites(
        structure,
        elements=settings.elements,
        symprec=settings.symprec,
    )
    if not sites:
        raise ValueError(
            "No symmetry-inequivalent C/N/O sites to excite. "
            f"Requested elements: {', '.join(settings.elements)}."
        )
    supercell = "×".join(str(n) for n in settings.supercell)
    kpts = "×".join(str(n) for n in settings.kpts)
    charge_note = (
        "charge-neutral (extra electron in the conduction band, GPAW charge=-1)"
        if settings.charge_mode == "neutral"
        else "charged cell (core electron removed, GPAW charge=0; neutralizing background)"
    )
    steps = [
        DscfStep(
            key="neutral_sp",
            kind=StepKind.NEUTRAL_SP,
            title="Ground state · neutral cell",
            user_hint=(
                f"GPAW ground state, {settings.xc}, plane-wave cutoff "
                f"{settings.pw_cutoff_ev:.0f} eV, k-points {kpts}, "
                f"supercell {supercell}. Records E₀, the Fermi level, and the band edges."
            ),
            status=StepStatus.QUEUED,
            route=(
                f"GPAW {settings.xc} PW({settings.pw_cutoff_ev:.0f} eV) "
                f"kpts={kpts} supercell={supercell}"
            ),
            gjf_name=f"job_{job_id}_neutral.py",
            log_name=f"job_{job_id}_neutral.txt",
            weight=1,
        )
    ]
    for n, site in enumerate(sites, start=1):
        label = f"{site.element}{site.index + 1}"
        steps.append(
            DscfStep(
                key=f"corehole_{site.index}",
                kind=StepKind.COREHOLE_SP,
                title=f"Core hole · {label} ×{site.multiplicity}",
                user_hint=(
                    f"Full 1s core hole on {label} (setup {settings.setup_name}), "
                    f"{charge_note}. This site stands for {site.multiplicity} "
                    "symmetry-equivalent atom(s). "
                    "BE = E(core hole) − E₀, including GPAW reference energies."
                ),
                status=StepStatus.WAITING,
                route=(
                    f"GPAW core-hole {label} setup={settings.setup_name} "
                    f"charge_mode={settings.charge_mode}"
                ),
                gjf_name=f"job_{job_id}_corehole_{label}.py",
                log_name=f"job_{job_id}_corehole_{label}.txt",
                atom_index=site.index,
                element=site.element,
                weight=site.multiplicity,
            )
        )
    return steps, sites


def band_edges(
    eigenvalues: list[float] | None,
    occupations: list[float] | None,
) -> tuple[float | None, float | None]:
    """Ground-state VBM and CBM from GPAW eigenvalues and occupations.

    A spin-paired band holds up to 2 electrons; a spin-polarized band holds 1.
    VBM is the highest eigenvalue that is at least half filled. CBM is the
    lowest eigenvalue that is not.
    """
    if not eigenvalues or not occupations or len(eigenvalues) != len(occupations):
        return None, None
    filled = max(float(o) for o in occupations)
    # GPAW reports occupations up to 2 (spin-paired) or 1 (spin-polarized).
    half = 1.0 if filled > 1.5 else 0.5
    vbm = None
    cbm = None
    for energy, occ in sorted(zip(eigenvalues, occupations, strict=True)):
        if float(occ) >= half - 1e-8:
            vbm = float(energy)
        elif cbm is None:
            cbm = float(energy)
    return vbm, cbm


def referenced_delta(
    be_raw_ev: float,
    *,
    mode: str,
    charge_mode: str,
    fermi_ev: float | None,
    vbm_ev: float | None,
    cbm_ev: float | None,
) -> tuple[float, str]:
    """Map a raw ΔSCF energy (eV) onto the selected periodic reference."""
    chosen = (mode or "absolute").strip().lower()
    neutral = (charge_mode or "neutral").strip().lower() == "neutral"
    if chosen in {"absolute", "global", "per_element"}:
        return be_raw_ev, ""
    if chosen == "fermi":
        if neutral:
            return be_raw_ev, (
                "Neutral ΔSCF: the photoelectron is in the conduction band, so "
                "E_core−E_0 is the Fermi-referenced binding energy for a metal "
                "(Susi et al.). On a gapped solid the electron sits at the CBM; "
                "VBM mode adds the ground-state gap."
            )
        if fermi_ev is None:
            raise ValueError("Fermi reference needs the ground-state Fermi energy")
        return be_raw_ev - float(fermi_ev), (
            "Charged ΔSCF minus the ground-state Fermi energy. "
            "The charged cell has a neutralizing background, so this is not vacuum-aligned."
        )
    if chosen == "vbm":
        if vbm_ev is None:
            raise ValueError("VBM reference needs a ground-state valence-band maximum")
        if neutral:
            gap = 0.0 if cbm_ev is None else max(float(cbm_ev) - float(vbm_ev), 0.0)
            return be_raw_ev + gap, (
                "Neutral ΔSCF plus the ground-state gap (CBM−VBM). "
                "This estimates the binding energy relative to the VBM when the "
                "extra electron sits at the CBM. It is not a potential-alignment correction."
            )
        return be_raw_ev - float(vbm_ev), (
            "Charged ΔSCF minus the ground-state VBM. "
            "The charged cell has a neutralizing background, so this is not vacuum-aligned."
        )
    raise ValueError(f"Unknown reference mode {mode!r}")


@dataclass
class ScfEnergy:
    """One GPAW total energy, already including ``get_reference_energy()``."""

    total_ev: float
    fermi_ev: float | None = None
    eigenvalues: list[float] | None = None
    occupations: list[float] | None = None


@dataclass
class HoleEnergy:
    atom_index: int
    element: str
    multiplicity: int
    energy_ev: float


@dataclass
class GpawReport:
    levels: list[CoreLevel]
    reference: dict[str, Any]
    e0_ev: float
    fermi_ev: float | None
    vbm_ev: float | None
    cbm_ev: float | None
    charge_mode: str
    notes: list[str] = field(default_factory=list)


def build_levels(
    *,
    e0_ev: float,
    holes: list[HoleEnergy],
    settings: GpawSettings,
    fermi_ev: float | None = None,
    vbm_ev: float | None = None,
    cbm_ev: float | None = None,
) -> GpawReport:
    """Binding energies and the reference actually applied."""
    mode = settings.reference_mode
    note = ""
    levels: list[CoreLevel] = []
    for hole in holes:
        be_raw = float(hole.energy_ev) - float(e0_ev)
        be_ref, note = referenced_delta(
            be_raw,
            mode=mode if mode in {"fermi", "vbm"} else "absolute",
            charge_mode=settings.charge_mode,
            fermi_ev=fermi_ev,
            vbm_ev=vbm_ev,
            cbm_ev=cbm_ev,
        )
        # For Fermi/VBM the value to plot is be_ref. Global / per-element
        # shifts are applied afterwards to the raw ΔE (absolute mode) or, if
        # the user picked fermi/vbm, those are the final values.
        use = be_ref if mode in {"fermi", "vbm"} else be_raw
        levels.append(
            CoreLevel(
                element=hole.element,
                atom_index=hole.atom_index,
                orbital_index=0,
                energy_ha=0.0,
                binding_ev_raw=be_raw,
                binding_ev_scaled=use,
                binding_ev_shifted=use,
                binding_ev_final=use,
                weight=float(hole.multiplicity),
                reference_mode=mode if mode in {"fermi", "vbm"} else "",
            )
        )
    if mode in {"absolute", "global", "per_element"}:
        info = apply_be_reference(
            levels,
            mode,
            refs=element_references(
                c1s=settings.c1s_ref_ev,
                n1s=settings.n1s_ref_ev,
                o1s=settings.o1s_ref_ev,
            ),
            reference_element=settings.reference_element,
        )
    else:
        info = {
            "mode": mode,
            "note": note,
            "charge_mode": settings.charge_mode,
        }
        for lv in levels:
            lv.reference_mode = mode
    notes = [HA_NOTE]
    if settings.charge_mode == "neutral":
        notes.append(
            "Default charge treatment is neutral: the core electron is placed in the "
            "conduction band (GPAW charge=-1 on a full 1s core-hole setup)."
        )
    else:
        notes.append(
            "Charged cell: the core electron is removed (GPAW charge=0 on a full 1s "
            "core-hole setup). Periodic GPAW compensates with a uniform background."
        )
    if settings.supercell == (1, 1, 1):
        notes.append(
            "Supercell is 1×1×1. Core-hole images interact; increase the supercell "
            "until the binding energies converge."
        )
    if note:
        notes.append(note)
    if info.get("note"):
        notes.append(str(info["note"]))
    info["charge_mode"] = settings.charge_mode
    info["fermi_ev"] = fermi_ev
    info["vbm_ev"] = vbm_ev
    info["cbm_ev"] = cbm_ev
    return GpawReport(
        levels=levels,
        reference=info,
        e0_ev=float(e0_ev),
        fermi_ev=fermi_ev,
        vbm_ev=vbm_ev,
        cbm_ev=cbm_ev,
        charge_mode=settings.charge_mode,
        notes=notes,
    )


def run_structure(structure: PeriodicStructure, settings: GpawSettings, evaluator) -> GpawReport:
    """Ground state plus one core hole per inequivalent site.

    ``evaluator(structure, keywords) -> ScfEnergy`` performs one SCF.
    The real GPAW evaluator lives in the service layer so this module stays
    importable without GPAW.
    """
    supercell = make_supercell(structure, settings.supercell)
    neutral_kw = calculator_keywords(settings, kind="neutral", atom_index=None, txt="-")
    neutral_kw["setup_dir"] = settings.setup_dir
    neutral = evaluator(supercell, neutral_kw)
    vbm, cbm = band_edges(neutral.eigenvalues, neutral.occupations)
    sites = inequivalent_sites(structure, elements=settings.elements, symprec=settings.symprec)
    holes: list[HoleEnergy] = []
    for site in sites:
        keywords = calculator_keywords(settings, kind="corehole", atom_index=site.index, txt="-")
        keywords["setup_dir"] = settings.setup_dir
        result = evaluator(supercell, keywords)
        holes.append(
            HoleEnergy(
                atom_index=site.index,
                element=site.element,
                multiplicity=site.multiplicity,
                energy_ev=float(result.total_ev),
            )
        )
    return build_levels(
        e0_ev=float(neutral.total_ev),
        holes=holes,
        settings=settings,
        fermi_ev=neutral.fermi_ev,
        vbm_ev=vbm,
        cbm_ev=cbm,
    )


def render_gpaw_script(keywords: dict[str, Any], *, title: str) -> str:
    """Human-readable script of the GPAW call. The runner uses the same keywords."""
    lines = [
        '"""Generated by Quanta. Re-run with GPAW on PYTHONPATH and the core-hole setups installed."""',
        title,
        "from ase.io import read",
        "from gpaw import GPAW, PW, FermiDirac, setup_paths",
        "",
    ]
    if keywords.get("setup_dir"):
        lines.append(f"setup_paths.insert(0, {keywords['setup_dir']!r})")
    lines.append(f"atoms = read({keywords['structure']!r})")
    repeat = keywords.get("supercell")
    if repeat and tuple(repeat) != (1, 1, 1):
        lines.append(f"atoms = atoms * {tuple(repeat)}")
    occ = keywords["occupations"]
    fix = ", fixmagmom=True" if occ.get("fixmagmom") else ""
    args = [
        f"mode=PW({keywords['mode']['cutoff_ev']})",
        f"xc={keywords['xc']!r}",
        f"kpts={tuple(keywords['kpts'])}",
        f"charge={keywords['charge']}",
        f"txt={keywords['txt']!r}",
        f"occupations=FermiDirac({occ['width_ev']}{fix})",
    ]
    if keywords.get("spinpol"):
        args.append("spinpol=True")
    if keywords.get("setups"):
        args.append(f"setups={keywords['setups']!r}")
    if keywords.get("symmetry"):
        args.append(f"symmetry={keywords['symmetry']!r}")
    joined = ",\n    ".join(args)
    lines.append(f"calc = GPAW(\n    {joined},\n)")
    if keywords.get("magmom_atom") is not None:
        lines.append(f"atoms[{keywords['magmom_atom']}].magmom = {keywords['magmom']}")
    lines.append("atoms.calc = calc")
    lines.append("energy = atoms.get_potential_energy() + calc.get_reference_energy()")
    lines.append("print(energy)")
    return "\n".join(lines) + "\n"
