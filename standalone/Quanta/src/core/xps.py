"""L2 — XPS stick → continuum spectrum (Gaussian / Lorentzian / Voigt / PseudoVoigt)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from src.core.models import CoreLevel, Orbital

PeakProfile = Literal["gaussian", "lorentzian", "voigt", "pseudovoigt"]

PEAK_PROFILES: tuple[PeakProfile, ...] = (
    "gaussian",
    "lorentzian",
    "voigt",
    "pseudovoigt",
)

# Approximate 1s eigenvalue windows (Hartree) for assignment after OPT/pop=full
CORE_WINDOWS_HA = {
    "C": (-12.0, -9.0),
    "N": (-16.0, -13.0),
    "O": (-21.0, -18.0),
}

REF_C1S_EV = 284.3
REF_O1S_EV = 530.6
REF_N1S_EV = 399.3

_FWHM_TO_SIGMA_G = 2.0 * math.sqrt(2.0 * math.log(2.0))  # ≈ 2.3548


@dataclass
class XpsSettings:
    scale: float = 1.024
    c1s_ref_ev: float = REF_C1S_EV
    fwhm_ev: float = 1.2
    apply_linear_map: bool = False
    c1s_slope: float = 0.74
    o1s_slope: float = 0.96
    n1s_slope: float = 1.5


@dataclass(frozen=True)
class SpectrumParams:
    """Global lineshape applied to every stick peak."""

    profile: PeakProfile = "pseudovoigt"
    fwhm_ev: float = 1.2
    # PseudoVoigt / Voigt mixing: 0 = Gaussian, 1 = Lorentzian.
    fraction: float = 0.5
    step_ev: float = 0.05
    pad_ev: float = 3.0


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
    """Legacy Yamada map (kept for old tests; ΔSCF path does not use this)."""
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


def _gauss_sigma(fwhm: float) -> float:
    return fwhm / _FWHM_TO_SIGMA_G


def _lorentz_gamma(fwhm: float) -> float:
    return fwhm / 2.0


def peak_gaussian(x: np.ndarray, center: float, fwhm: float, intensity: float = 1.0) -> np.ndarray:
    sigma = _gauss_sigma(fwhm)
    return intensity * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def peak_lorentzian(x: np.ndarray, center: float, fwhm: float, intensity: float = 1.0) -> np.ndarray:
    gamma = _lorentz_gamma(fwhm)
    return intensity * (gamma**2 / ((x - center) ** 2 + gamma**2))


def peak_pseudovoigt(
    x: np.ndarray,
    center: float,
    fwhm: float,
    intensity: float = 1.0,
    fraction: float = 0.5,
) -> np.ndarray:
    """GL(m)-style mix: fraction 0 = Gaussian, 1 = Lorentzian (same FWHM)."""
    f = float(np.clip(fraction, 0.0, 1.0))
    g = peak_gaussian(x, center, fwhm, intensity=1.0)
    lor = peak_lorentzian(x, center, fwhm, intensity=1.0)
    return intensity * ((1.0 - f) * g + f * lor)


def peak_voigt(
    x: np.ndarray,
    center: float,
    fwhm: float,
    intensity: float = 1.0,
    fraction: float = 0.5,
) -> np.ndarray:
    """True Voigt via Faddeeva when scipy is available; else PseudoVoigt."""
    f = float(np.clip(fraction, 0.0, 1.0))
    fwhm_g = max((1.0 - f) * fwhm, 1e-9)
    fwhm_l = max(f * fwhm, 1e-9)
    sigma = _gauss_sigma(fwhm_g)
    gamma = _lorentz_gamma(fwhm_l)
    try:
        from scipy.special import wofz  # type: ignore

        z = ((x - center) + 1j * gamma) / (sigma * math.sqrt(2.0))
        y = np.real(wofz(z)) / (sigma * math.sqrt(2.0 * math.pi))
        y0 = float(
            np.real(wofz(1j * gamma / (sigma * math.sqrt(2.0))))
            / (sigma * math.sqrt(2.0 * math.pi))
        )
        if y0 > 1e-30:
            y = y / y0
        return intensity * y
    except Exception:
        return peak_pseudovoigt(x, center, fwhm, intensity=intensity, fraction=fraction)


def peak_profile(
    x: np.ndarray,
    center: float,
    *,
    profile: PeakProfile,
    fwhm: float,
    intensity: float = 1.0,
    fraction: float = 0.5,
) -> np.ndarray:
    if profile == "gaussian":
        return peak_gaussian(x, center, fwhm, intensity)
    if profile == "lorentzian":
        return peak_lorentzian(x, center, fwhm, intensity)
    if profile == "voigt":
        return peak_voigt(x, center, fwhm, intensity, fraction=fraction)
    return peak_pseudovoigt(x, center, fwhm, intensity, fraction=fraction)


def voigt_pseudo(x: np.ndarray, center: float, fwhm: float, intensity: float = 1.0) -> np.ndarray:
    """Back-compat alias: fixed 50/50 PseudoVoigt."""
    return peak_pseudovoigt(x, center, fwhm, intensity, fraction=0.5)


def simulate_spectrum(
    levels: list[CoreLevel],
    element: str,
    fwhm: float = 1.2,
    step: float = 0.05,
    pad: float = 3.0,
    *,
    profile: PeakProfile = "pseudovoigt",
    fraction: float = 0.5,
    params: SpectrumParams | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Sum equal-height peaks at each atom BE for one element."""
    if params is not None:
        profile = params.profile
        fwhm = params.fwhm_ev
        fraction = params.fraction
        step = params.step_ev
        pad = params.pad_ev

    subset = [lv for lv in levels if lv.element == element]
    if not subset:
        return np.array([]), np.array([])
    centers = [lv.binding_ev_final for lv in subset]
    xmin, xmax = min(centers) - pad, max(centers) + pad
    x = np.arange(xmin, xmax + step, step)
    y = np.zeros_like(x, dtype=float)
    for c in centers:
        y += peak_profile(
            x, c, profile=profile, fwhm=fwhm, intensity=1.0, fraction=fraction
        )
    return x, y


def levels_from_summary_rows(rows: list[dict]) -> list[CoreLevel]:
    """Rebuild CoreLevel list from curated summary JSON rows."""
    out: list[CoreLevel] = []
    for row in rows:
        be = float(row.get("be_final_ev", row.get("be_shifted_ev", row.get("be_raw_ev", 0.0))))
        raw = float(row.get("be_raw_ev", be))
        shifted = float(row.get("be_shifted_ev", be))
        out.append(
            CoreLevel(
                element=str(row.get("element") or ""),
                atom_index=row.get("atom_index"),
                orbital_index=None,
                energy_ha=0.0,
                binding_ev_raw=raw,
                binding_ev_scaled=raw,
                binding_ev_shifted=shifted,
                binding_ev_final=be,
            )
        )
    return out
