"""Unit tests for ΔSCF workflow planning and BE extraction."""

from __future__ import annotations

from src.core.dscf import (
    DscfSettings,
    assign_core_orbitals,
    build_workflow_steps,
    compute_binding_energies,
    homo_orbital_index,
    list_xps_atoms,
)
from src.core.models import Orbital


def test_list_xps_atoms():
    atoms = [("C", 0, 0, 0), ("H", 1, 0, 0), ("N", 0, 1, 0), ("O", 0, 0, 1)]
    assert list_xps_atoms(atoms) == [(0, "C"), (2, "N"), (3, "O")]


def test_build_workflow_steps_counts():
    atoms = [("C", 0, 0, 0), ("N", 0, 1, 0), ("N", 0, 2, 0)]
    steps = build_workflow_steps(atoms, DscfSettings(), job_id=7)
    assert len(steps) == 2 + 3  # opt + neutral + 3 coreholes
    assert steps[0].key == "opt"
    assert steps[1].key == "neutral_sp"
    assert steps[2].kind.value == "corehole_sp"


def test_corehole_charge_multiplicity_for_closed_shell():
    from src.core.dscf import corehole_charge_multiplicity

    # Ethane: 18 e⁻ neutral singlet → 17 e⁻ cation doublet
    assert corehole_charge_multiplicity(0, 1) == (1, 2)
    # Radical neutral doublet → even-electron cation singlet
    assert corehole_charge_multiplicity(0, 2) == (1, 1)
    assert corehole_charge_multiplicity(-1, 1) == (0, 2)


def test_assign_core_orbitals_and_be():
    orbitals = [
        Orbital(index=1, energy_ha=-11.0, occupancy=2.0),
        Orbital(index=2, energy_ha=-10.5, occupancy=2.0),
        Orbital(index=3, energy_ha=-0.5, occupancy=2.0),
        Orbital(index=4, energy_ha=0.2, occupancy=0.0),
    ]
    xps_atoms = [(0, "C"), (1, "C")]
    mapping = assign_core_orbitals(orbitals, xps_atoms)
    assert mapping == {0: 1, 1: 2}
    assert homo_orbital_index(orbitals) == 3

    levels = compute_binding_energies(
        e0_ha=-100.0,
        corehole_energies=[(0, "C", -99.5), (1, "C", -99.4)],
        apply_c1s_shift=False,
    )
    assert len(levels) == 2
    assert levels[0].binding_ev_final > 0
