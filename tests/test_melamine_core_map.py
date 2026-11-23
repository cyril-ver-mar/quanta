"""Melamine: 1s MOs belong to the atom that carries the 1s population."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.core.dscf import list_xps_atoms
from src.core.gaussian_mos import (
    pipek_mezey_1s,
    resolve_core_orbitals,
    s1_population,
)
from src.services.gaussian_parser import parse_gaussian_log, read_log_text
from src.core.gaussian_mos import parse_population

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "fixtures" / "melanine" / "MELANINE.LOG"

# Atom order in fixtures/melanine/melanine.gjf (0-based).
ATOMS = [
    ("C", 1.3216, 0.0, 0.0),
    ("N", 0.694, 1.2021, 0.0),
    ("C", -0.6608, 1.1445, 0.0),
    ("N", -1.388, 0.0, 0.0),
    ("C", -0.6608, -1.1445, 0.0),
    ("N", 0.694, -1.2021, 0.0),
    ("N", -1.3908, 2.4089, 0.0),
    ("N", -1.3908, -2.4089, 0.0),
    ("N", 2.7816, 0.0, 0.0),
    ("H", 0.0, 0.0, 0.0),
    ("H", 0.0, 0.0, 0.0),
    ("H", 0.0, 0.0, 0.0),
    ("H", 0.0, 0.0, 0.0),
    ("H", 0.0, 0.0, 0.0),
    ("H", 0.0, 0.0, 0.0),
]


def test_melamine_does_not_give_carbon_the_nitrogen_1s() -> None:
    text = read_log_text(LOG)
    parsed = parse_gaussian_log(LOG)
    population = parse_population(text)
    assert population.alpha is not None
    xps = list_xps_atoms(ATOMS)
    mapping = resolve_core_orbitals(parsed.orbitals, xps, population)

    # The bug: sorting occupied MOs by energy and zipping with input order
    # handed C1 (atom 1) the deepest MO, an N 1s near −14.3 Ha.
    c1_mo = mapping.by_atom[0]
    c1_energy = float(population.alpha.eigenvalues[c1_mo - 1])
    assert c1_energy > -12.0, c1_energy
    assert c1_mo != 1

    for atom, element in xps:
        mo = mapping.by_atom[atom]
        energy = float(population.alpha.eigenvalues[mo - 1])
        if element == "C":
            assert -12.5 < energy < -8.0, (atom, mo, energy)
        else:
            assert energy < -12.0, (atom, mo, energy)
        pop = mapping.population[atom]
        assert pop >= 0.8, (atom, element, mo, pop)

    assert mapping.guess_style == "cards"
    assert mapping.coefficients is not None
    # Localized column really sits on that atom.
    for atom, _element in xps:
        mo = mapping.by_atom[atom] - 1
        assert s1_population(mapping.coefficients, population.alpha.basis, atom, mo) >= 0.8


def test_pipek_mezey_splits_a_two_atom_core() -> None:
    basis_atom = [0, 1]
    # Two delocalized 1s combinations of atoms 0 and 1.
    s = 2 ** -0.5
    coeff = np.array([[s, s], [s, -s]], dtype=float)  # (nbf, nmo) — wait rows are basis
    # basis function 0 is atom 0, basis function 1 is atom 1.
    # MO0 = (1, 1)/sqrt(2), MO1 = (1, -1)/sqrt(2). Shape (2, 2).
    from src.core.gaussian_mos import BasisFn

    basis = [
        BasisFn(index=1, atom_index=0, element="C", shell="1S"),
        BasisFn(index=2, atom_index=1, element="C", shell="1S"),
    ]
    localized, rotated = pipek_mezey_1s(coeff, basis, [0, 1], [0, 1])
    assert rotated > 1e-3
    pops = [s1_population(localized, basis, atom, mo) for atom in (0, 1) for mo in (0, 1)]
    assert max(pops) > 0.95
    # Each MO is on one atom.
    assert s1_population(localized, basis, 0, 0) > 0.95 or s1_population(localized, basis, 0, 1) > 0.95
    _ = basis_atom
