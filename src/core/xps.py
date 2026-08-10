"""L2 — XPS spectrum helpers (Yamada & Sato TANSO 2015 style)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from src.core.models import CoreLevel, Orbital

# Approximate 1s eigenvalue windows (Hartree) for assignment after OPT/pop=full
CORE_WINDOWS_HA = {
    "C": (-12.0, -9.0),
    "N": (-16.0, -13.0),
    "O": (-21.0, -18.0),
}

# Literature absolute anchors used in the paper (eV)
REF_C1S_EV = 284.3
REF_O1S_EV = 530.6  # C=O
REF_N1S_EV = 399.3  # sp2C-NH2


@dataclass
class XpsSettings:
    scale: float = 1.024
    c1s_ref_ev: float = REF_C1S_EV
    fwhm_ev: float = 1.2
    apply_linear_map: bool = False
    c1s_slope: float = 0.74
    o1s_slope: float = 0.96
    n1s_slope: float = 1.5


def hartree_to_ev(e_ha: float) -> float:
    return -e_ha * 27.211386245988


def assign_core_levels(
    orbitals: list[Orbital],
    element_counts: dict[str, int] | None = None,
) -> list[CoreLevel]:
    """Pick deep occupied MOs in element windows (Koopmans-like cores)."""
    occupied = [o for o in orbitals if o.occupancy > 0.1]
    occupied = sorted(occupied, key=lambda o: o.energy_ha)
    results: list[CoreLevel] = []
    used: set[int] = set()

    for element, (lo, hi) in CORE_WINDOWS_HA.items():
        candidates = [o for o in occupied if lo <= o.energy_ha <= hi and o.index not in used]
        n_need = (element_counts or {}).get(element)
        if n_need is not None:
            candidates = candidates[:n_need]
        for orb in candidates:
            used.add(orb.index)
            be = hartree_to_ev(orb.energy_ha)
            results.append(
                CoreLevel(
                    element=element,
                    atom_index=None,
                    orbital_index=orb.index,
                    energy_ha=orb.energy_ha,
                    binding_ev_raw=be,
                    binding_ev_scaled=be,
                    binding_ev_shifted=be,
                    binding_ev_final=be,
                )
            )
    return results


def _mean_be(levels: list[CoreLevel], element: str) -> float | None:
    vals = [lv.binding_ev_scaled for lv in levels if lv.element == element]
    if not vals:
        return None
    return sum(vals) / len(vals)


def apply_yamada_corrections(levels: list[CoreLevel], settings: XpsSettings) -> list[CoreLevel]:
    """
    1) scale calculated BE
    2) rigid shift so mean C1s → c1s_ref (paper: sp2C-sp2C → 284.3 eV)
    3) optional linear map on relative positions (paper Figs. 4–6)
    """
    if not levels:
        return levels

    scaled = [
        CoreLevel(
            element=lv.element,
            atom_index=lv.atom_index,
            orbital_index=lv.orbital_index,
            energy_ha=lv.energy_ha,
            binding_ev_raw=lv.binding_ev_raw,
            binding_ev_scaled=lv.binding_ev_raw * settings.scale,
            binding_ev_shifted=0.0,
            binding_ev_final=0.0,
        )
        for lv in levels
    ]

    c_mean = _mean_be(scaled, "C")
    shift = (settings.c1s_ref_ev - c_mean) if c_mean is not None else 0.0

    for lv in scaled:
        lv.binding_ev_shifted = lv.binding_ev_scaled + shift

    if not settings.apply_linear_map:
        for lv in scaled:
            lv.binding_ev_final = lv.binding_ev_shifted
        return scaled

    o_vals = [lv.binding_ev_shifted for lv in scaled if lv.element == "O"]
    n_vals = [lv.binding_ev_shifted for lv in scaled if lv.element == "N"]
    o_mean = sum(o_vals) / len(o_vals) if o_vals else None
    n_mean = sum(n_vals) / len(n_vals) if n_vals else None

    for lv in scaled:
        if lv.element == "C":
            rel = lv.binding_ev_shifted - settings.c1s_ref_ev
            lv.binding_ev_final = settings.c1s_ref_ev + settings.c1s_slope * rel
        elif lv.element == "O" and o_mean is not None:
            rel = lv.binding_ev_shifted - o_mean
            lv.binding_ev_final = REF_O1S_EV + settings.o1s_slope * rel
        elif lv.element == "N" and n_mean is not None:
            rel = lv.binding_ev_shifted - n_mean
            lv.binding_ev_final = REF_N1S_EV + settings.n1s_slope * rel
        else:
            lv.binding_ev_final = lv.binding_ev_shifted
    return scaled


def voigt_pseudo(x: np.ndarray, center: float, fwhm: float, intensity: float = 1.0) -> np.ndarray:
    """Pseudo-Voigt (50/50 Gauss-Lorentz) peak."""
    sigma = fwhm / (2 * math.sqrt(2 * math.log(2)))
    gamma = fwhm / 2.0
    gauss = np.exp(-0.5 * ((x - center) / sigma) ** 2)
    lorentz = gamma**2 / ((x - center) ** 2 + gamma**2)
    return intensity * (0.5 * gauss + 0.5 * lorentz)


def simulate_spectrum(
    levels: list[CoreLevel],
    element: str,
    fwhm: float = 1.2,
    step: float = 0.05,
    pad: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    subset = [lv for lv in levels if lv.element == element]
    if not subset:
        return np.array([]), np.array([])
    centers = [lv.binding_ev_final for lv in subset]
    xmin, xmax = min(centers) - pad, max(centers) + pad
    x = np.arange(xmin, xmax + step, step)
    y = np.zeros_like(x)
    for c in centers:
        y += voigt_pseudo(x, c, fwhm)
    return x, y
