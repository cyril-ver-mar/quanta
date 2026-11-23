"""Binding-energy reference conventions.

Absolute ΔSCF energies are always kept. A reference is applied only when the
user selects one:

* ``absolute`` — raw ΔE, no shift
* ``global`` — one constant, from the mean of a chosen element to a chosen
  value, added to every peak (spectrometer-style calibration)
* ``per_element`` — each element is shifted so its own mean matches that
  element's reference. Chemical shifts *within* an element are kept; the
  gap between elements is replaced by the gap between the references
* ``fermi`` / ``vbm`` — periodic GPAW conventions (see :mod:`src.core.engines.gpaw`)
"""

from __future__ import annotations

from typing import Any

from src.core.models import CoreLevel

REF_C1S_EV = 284.3
REF_N1S_EV = 399.3
REF_O1S_EV = 530.6

REFERENCE_MODES = ("absolute", "global", "per_element", "fermi", "vbm")


def element_references(
    *,
    c1s: float = REF_C1S_EV,
    n1s: float = REF_N1S_EV,
    o1s: float = REF_O1S_EV,
) -> dict[str, float]:
    return {"C": float(c1s), "N": float(n1s), "O": float(o1s)}


def _weighted_mean(levels: list[CoreLevel], element: str) -> float | None:
    vals = [(lv.binding_ev_raw, float(lv.weight or 1.0)) for lv in levels if lv.element == element]
    weight = sum(w for _v, w in vals)
    if weight <= 0 or not vals:
        return None
    return sum(v * w for v, w in vals) / weight


def apply_be_reference(
    levels: list[CoreLevel],
    mode: str,
    *,
    refs: dict[str, float] | None = None,
    reference_element: str = "C",
) -> dict[str, Any]:
    """Set ``binding_ev_final`` from ``binding_ev_raw``. Returns a description."""
    chosen = (mode or "absolute").strip().lower()
    if chosen not in REFERENCE_MODES:
        raise ValueError(f"Unknown BE reference mode {mode!r}. Choose from {REFERENCE_MODES}.")
    table = dict(refs or element_references())
    info: dict[str, Any] = {"mode": chosen, "element_refs_ev": table}

    for lv in levels:
        lv.binding_ev_shifted = lv.binding_ev_raw
        lv.binding_ev_final = lv.binding_ev_raw
        lv.reference_mode = chosen

    if chosen == "absolute":
        info["note"] = (
            "Absolute ΔSCF binding energies (no shift). "
            "Gas-phase values are not aligned to an experimental reference."
        )
        return info

    if chosen == "global":
        element = (reference_element or "C").strip()
        mean = _weighted_mean(levels, element)
        target = table.get(element)
        if mean is None or target is None:
            info["warning"] = (
                f"No {element} levels to calibrate against. Binding energies were left absolute."
            )
            info["mode"] = "absolute"
            for lv in levels:
                lv.reference_mode = "absolute"
            return info
        shift = float(target) - mean
        for lv in levels:
            lv.binding_ev_shifted = lv.binding_ev_raw + shift
            lv.binding_ev_final = lv.binding_ev_shifted
        info.update(
            {
                "reference_element": element,
                "target_ev": float(target),
                "mean_raw_ev": mean,
                "shift_ev": shift,
                "note": (
                    f"One calibration shift ({shift:+.3f} eV) was added to every peak so the "
                    f"weighted mean {element}1s equals {target:.3f} eV. "
                    "Relative binding energies between elements are unchanged."
                ),
            }
        )
        return info

    if chosen == "per_element":
        shifts: dict[str, float] = {}
        for element, target in table.items():
            mean = _weighted_mean(levels, element)
            if mean is None:
                continue
            shifts[element] = float(target) - mean
        for lv in levels:
            shift = shifts.get(lv.element, 0.0)
            lv.binding_ev_shifted = lv.binding_ev_raw + shift
            lv.binding_ev_final = lv.binding_ev_shifted
        info.update(
            {
                "shifts_ev": shifts,
                "note": (
                    "Each element was shifted so its weighted mean matches that element's "
                    "reference. Chemical shifts within one element are kept; the gap between "
                    "elements is the gap between the references, not the raw ΔSCF gap."
                ),
            }
        )
        return info

    # fermi / vbm: the periodic engine has already placed the referenced value
    # in binding_ev_raw when it asks for those modes. Callers that want the
    # raw ΔE as well pass it separately and set final here only for the
    # molecular modes. Leave values unchanged and record the mode.
    info["note"] = (
        "Fermi/VBM referencing is applied by the periodic engine from the "
        "ground-state eigenvalues. See the GPAW result notes."
    )
    return info
