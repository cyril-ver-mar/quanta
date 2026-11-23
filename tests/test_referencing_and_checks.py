"""Reference modes and core-hole collapse checks."""

from __future__ import annotations

import numpy as np

from src.core.dscf import compute_binding_energies
from src.core.gaussian_mos import (
    BasisFn,
    GaussianPopulation,
    MoSet,
    assess_core_hole,
    be_in_window,
    format_guess_cards,
    fortran_e20_8,
)
from src.core.referencing import apply_be_reference


def test_global_shift_is_one_constant_and_absolute_is_raw() -> None:
    levels = compute_binding_energies(
        e0_ha=-100.0,
        corehole_energies=[(0, "C", -89.5), (1, "N", -85.0)],
        apply_c1s_shift=False,
        reference_mode="absolute",
    )
    raw_c = levels[0].binding_ev_final
    raw_n = levels[1].binding_ev_final
    assert levels[0].binding_ev_final == levels[0].binding_ev_raw

    shifted = compute_binding_energies(
        e0_ha=-100.0,
        corehole_energies=[(0, "C", -89.5), (1, "N", -85.0)],
        c1s_ref_ev=284.3,
        reference_mode="global",
        reference_element="C",
    )
    delta = shifted[0].binding_ev_final - raw_c
    assert abs(shifted[0].binding_ev_final - 284.3) < 1e-6
    assert abs((shifted[1].binding_ev_final - raw_n) - delta) < 1e-6


def test_per_element_shifts_are_independent() -> None:
    levels = compute_binding_energies(
        e0_ha=-100.0,
        corehole_energies=[(0, "C", -89.5), (1, "N", -85.0)],
        reference_mode="per_element",
        c1s_ref_ev=284.3,
        n1s_ref_ev=399.3,
    )
    assert abs(levels[0].binding_ev_final - 284.3) < 1e-6
    assert abs(levels[1].binding_ev_final - 399.3) < 1e-6
    # The N−C gap is the reference gap, not the raw gap.
    raw = compute_binding_energies(
        e0_ha=-100.0,
        corehole_energies=[(0, "C", -89.5), (1, "N", -85.0)],
        reference_mode="absolute",
    )
    assert abs((levels[1].binding_ev_final - levels[0].binding_ev_final) - (399.3 - 284.3)) < 1e-6
    assert abs(raw[1].binding_ev_raw - raw[0].binding_ev_raw) != abs(399.3 - 284.3)


def test_mislabelled_nitrogen_is_outside_the_carbon_window() -> None:
    assert be_in_window("C", 290.0)
    assert not be_in_window("C", 400.0)
    assert not be_in_window("C", 20.0)
    assert be_in_window("N", 405.0)


def test_collapse_fails_spin_occupation_and_s2() -> None:
    basis = [BasisFn(1, 0, "C", "1S"), BasisFn(2, 1, "C", "1S")]
    # Alpha: MO0 is a filled C1 1s. Beta occupied MO0 is the same — no hole.
    coeff = np.array([[1.0, 0.0], [0.0, 1.0]])
    occupied = np.array([True, False])
    mos = MoSet(
        basis=basis,
        eigenvalues=np.array([-11.0, -0.2]),
        coefficients=coeff,
        occupied=occupied,
        spin="alpha",
    )
    bad = assess_core_hole(
        element="C",
        atom_index=0,
        multiplicity=2,
        be_raw_ev=15.0,
        population=GaussianPopulation(
            alpha=mos,
            beta=mos,
            s2=2.0,
            spin_density=[0.05, 0.9],
        ),
    )
    assert not bad.ok
    text = bad.message
    assert "S^2" in text or "<S^2>" in text
    assert "spin" in text.lower()
    assert "15.0" in text

    good_beta = MoSet(
        basis=basis,
        eigenvalues=np.array([-11.0, -0.2]),
        coefficients=np.array([[0.0, 1.0], [0.0, 0.0]]),
        occupied=np.array([True, False]),
        spin="beta",
    )
    # Beta occupied MO has no 1s on atom 0; the 1s column is virtual.
    good_beta.coefficients[:, 0] = np.array([0.0, 1.0])
    good_beta.occupied[:] = np.array([True, False])
    # Occupied beta MO is atom 1's 1s, not atom 0. Atom 0's 1s is virtual (column 1)
    # but column 1 is marked unoccupied and its eigenvalue is -0.2, so it is skipped.
    # Put the empty core eigenvalue on the virtual MO so a careless energy-only check
    # would still see it, and confirm we use the O/V label.
    good_beta.eigenvalues = np.array([-10.5, -11.2])
    good_beta.coefficients = np.array([[0.0, 1.0], [1.0, 0.0]])
    good = assess_core_hole(
        element="C",
        atom_index=0,
        multiplicity=2,
        be_raw_ev=291.0,
        population=GaussianPopulation(
            alpha=mos,
            beta=good_beta,
            s2=0.76,
            spin_density=[0.98, 0.02],
        ),
    )
    assert good.ok, good.message


def test_guess_cards_format_matches_gaussian_manual() -> None:
    alpha = np.array([[0.5, 0.1], [0.2, -0.3], [0.0, 0.4]])
    beta = alpha.copy()
    text = format_guess_cards(alpha, beta)
    lines = text.splitlines()
    assert lines[0] == "(4E20.8)"
    assert lines[1].strip() == "1"
    assert lines[-1].strip() == "0"
    # Two spins, so two terminator zeros.
    assert sum(1 for line in lines if line.strip() == "0") == 2
    field = fortran_e20_8(0.5)
    assert len(field) == 20
    assert "0.50000000E+00" in field


def test_apply_reference_records_the_mode() -> None:
    levels = compute_binding_energies(
        -10.0,
        [(0, "C", -9.0)],
        reference_mode="absolute",
    )
    info = apply_be_reference(levels, "absolute")
    assert info["mode"] == "absolute"
