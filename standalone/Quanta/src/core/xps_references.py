"""L2 — literature XPS reference sticks for plot overlays."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.utils.paths import FIXTURES_DIR

# XPS-Deconv default library (ASCII labels; C/N/O 1s only for Quanta overlays).
DECONV_KNOWN_PEAKS: dict[str, list[tuple[str, float]]] = {
    "C": [
        ("C-C / C-H", 284.80),
        ("Aromatic C", 284.46),
        ("C=C", 284.53),
        ("C-Si", 284.13),
        ("C-N", 285.74),
        ("C-N+", 285.91),
        ("C-NO2", 285.56),
        ("C*-C≡N", 286.21),
        ("C-O-C", 286.25),
        ("C-OH", 286.35),
        ("Epoxide", 286.82),
        ("C=O", 287.70),
        ("HO-(C=O)", 289.06),
        ("C-F", 287.71),
        ("CF2", 290.70),
        ("CF3", 292.49),
    ],
    "O": [
        ("Metal-O", 530.0),
        ("C-O / OH", 531.5),
        ("C=O / adsorbed", 532.5),
    ],
    "N": [
        ("Pyridinic-N", 398.5),
        ("Pyrrolic-N", 400.0),
        ("Graphitic-N", 401.3),
        ("Oxidized-N", 402.5),
        ("Melanine-N-center", 398.4),
        ("Melanine-NH-bridge", 399.0),
        ("Melanine-NH2-free", 400.2),
        ("Melanine-N-hetero", 401.2),
    ],
}


@dataclass(frozen=True)
class RefStick:
    label: str
    be_ev: float
    source: str  # "chong" | "deconv"


def _load_chong_reference() -> dict:
    path = FIXTURES_DIR / "chong2007" / "reference.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _is_chong_molecule(name: str | None, notes: str | None = None) -> bool:
    blob = f"{name or ''} {notes or ''}".lower()
    return "ethane" in blob or "hydrazine" in blob or "chong" in blob


def chong_reference_sticks(element: str) -> list[RefStick]:
    """Chong 2007 Table 1 observed CEBEs for ethane (C1s) / hydrazine (N1s)."""
    ref = _load_chong_reference()
    el = element.upper()
    out: list[RefStick] = []
    if el == "C":
        be = float(ref["molecules"]["ethane"]["chong_obs_ev"]["C1s"])
        out.append(RefStick("Chong ethane C1s (obs)", be, "chong"))
    elif el == "N":
        be = float(ref["molecules"]["hydrazine"]["chong_obs_ev"]["N1s"])
        out.append(RefStick("Chong hydrazine N1s (obs)", be, "chong"))
    return out


def deconv_reference_sticks(element: str) -> list[RefStick]:
    el = element.upper()
    return [
        RefStick(label, be, "deconv") for label, be in DECONV_KNOWN_PEAKS.get(el, [])
    ]


def reference_sticks_for_job(
    element: str,
    *,
    compound_name: str | None = None,
    compound_notes: str | None = None,
) -> list[RefStick]:
    """Chong for ethane/hydrazine; XPS-Deconv library for everything else."""
    if _is_chong_molecule(compound_name, compound_notes):
        sticks = chong_reference_sticks(element)
        if sticks:
            return sticks
    return deconv_reference_sticks(element)
