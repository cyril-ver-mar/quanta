"""Plan or run a periodic GPAW ΔSCF XPS calculation.

Example (layered C7N, once a CIF or POSCAR is available)::

    python scripts/gpaw_xps.py C7N.cif --supercell 2,2,1 --charge-mode neutral --reference fermi

Without ``--execute`` this only prints the inequivalent sites and the GPAW
settings. ``--execute`` needs GPAW, ASE, and full 1s core-hole setups on
``GPAW_SETUP_PATH`` (see the README).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.engines.gpaw import GpawSettings, plan_gpaw_steps  # noqa: E402
from src.core.periodic import parse_int_triple, read_periodic_structure  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Periodic ΔSCF XPS with GPAW")
    parser.add_argument("structure", help="CIF, POSCAR, or extxyz with a cell")
    parser.add_argument("--supercell", default="1,1,1", help="Repeat counts, e.g. 2,2,1")
    parser.add_argument("--kpts", default="1,1,1", help="k-point mesh, e.g. 2,2,1")
    parser.add_argument("--cutoff", type=float, default=500.0, help="Plane-wave cutoff in eV")
    parser.add_argument("--smearing", type=float, default=0.1, help="Fermi-Dirac width in eV")
    parser.add_argument("--xc", default="PBE")
    parser.add_argument(
        "--charge-mode",
        choices=("neutral", "charged"),
        default="neutral",
        help="neutral (default): extra electron in the conduction band; charged: electron removed",
    )
    parser.add_argument(
        "--reference",
        choices=("absolute", "fermi", "vbm", "global", "per_element"),
        default="absolute",
    )
    parser.add_argument("--elements", default="C,N", help="Elements to excite, e.g. C,N")
    parser.add_argument("--setup-name", default="fch1s")
    parser.add_argument("--setup-dir", default="", help="Directory of generated PAW setups")
    parser.add_argument("--execute", action="store_true", help="Run GPAW instead of only planning")
    args = parser.parse_args()

    structure = read_periodic_structure(args.structure)
    settings = GpawSettings(
        xc=args.xc,
        pw_cutoff_ev=args.cutoff,
        kpts=parse_int_triple(args.kpts, name="k-points"),
        supercell=parse_int_triple(args.supercell, name="supercell"),
        charge_mode=args.charge_mode,
        smearing_ev=args.smearing,
        setup_name=args.setup_name,
        setup_dir=args.setup_dir,
        elements=tuple(part.strip() for part in args.elements.split(",") if part.strip()),
        reference_mode=args.reference,
    )
    steps, sites = plan_gpaw_steps(structure, settings, job_id=0)
    print(f"Structure: {args.structure} ({structure.n_atoms} atoms)")
    print(f"Supercell: {settings.supercell}    k-points: {settings.kpts}    cutoff: {settings.pw_cutoff_ev} eV")
    print(f"Charge mode: {settings.charge_mode} (neutral is the default)")
    print(f"Reference: {settings.reference_mode}")
    print("Inequivalent sites:")
    for site in sites:
        print(f"  {site.element}{site.index + 1}  multiplicity {site.multiplicity}  atoms {[i + 1 for i in site.equivalents]}")
    print(f"Steps: {len(steps)} (1 ground state + {len(sites)} core holes)")
    if not args.execute:
        print("Dry run. Pass --execute to run GPAW.")
        return

    from src.core.engines.gpaw import run_structure
    from src.services.gpaw_runner import _gpaw_evaluator

    report = run_structure(structure, settings, _gpaw_evaluator)
    payload = {
        "e0_ev": report.e0_ev,
        "fermi_ev": report.fermi_ev,
        "vbm_ev": report.vbm_ev,
        "cbm_ev": report.cbm_ev,
        "charge_mode": report.charge_mode,
        "reference": report.reference,
        "notes": report.notes,
        "core_levels": [
            {
                "element": lv.element,
                "atom_index": lv.atom_index,
                "multiplicity": lv.weight,
                "be_raw_ev": lv.binding_ev_raw,
                "be_final_ev": lv.binding_ev_final,
            }
            for lv in report.levels
        ],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
