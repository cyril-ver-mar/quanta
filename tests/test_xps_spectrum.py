"""Tests for XPS peak profiles and reference selection."""

from __future__ import annotations

import numpy as np

from src.core.models import CoreLevel
from src.core.xps import SpectrumParams, peak_profile, simulate_spectrum
from src.core.xps_references import reference_sticks_for_job


def _level(element: str, be: float, atom: int = 0) -> CoreLevel:
    return CoreLevel(
        element=element,
        atom_index=atom,
        orbital_index=1,
        energy_ha=-11.0,
        binding_ev_raw=be,
        binding_ev_scaled=be,
        binding_ev_shifted=be,
        binding_ev_final=be,
    )


def test_profiles_peak_at_center() -> None:
    x = np.linspace(280, 290, 401)
    for profile in ("gaussian", "lorentzian", "pseudovoigt", "voigt"):
        y = peak_profile(x, 285.0, profile=profile, fwhm=1.2, fraction=0.5)  # type: ignore[arg-type]
        assert float(y[np.argmax(y)]) == float(np.max(y))
        assert abs(x[int(np.argmax(y))] - 285.0) < 0.05


def test_simulate_two_carbon_peaks() -> None:
    levels = [_level("C", 284.3, 0), _level("C", 286.0, 1)]
    x, y = simulate_spectrum(
        levels, "C", params=SpectrumParams(profile="gaussian", fwhm_ev=0.8)
    )
    assert len(x) == len(y) > 10
    assert float(np.max(y)) > 1.0  # two overlapping unit peaks


def test_chong_vs_deconv_refs() -> None:
    ethane = reference_sticks_for_job("C", compound_name="ethane")
    assert ethane and ethane[0].source == "chong"
    assert abs(ethane[0].be_ev - 290.72) < 0.01
    other = reference_sticks_for_job("C", compound_name="benzene")
    assert other and other[0].source == "deconv"
    hyd = reference_sticks_for_job("N", compound_name="hydrazine")
    assert hyd and hyd[0].source == "chong"
