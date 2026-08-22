"""Import Chong-2007 ethane / hydrazine smoke-test compounds into a project."""

from __future__ import annotations

import json

from src.core.project import QuantaProject
from src.services.compound_service import CompoundService
from src.services import project_service
from src.utils.paths import FIXTURES_DIR

CHONG_DIR = FIXTURES_DIR / "chong2007"


def load_chong_reference() -> dict:
    path = CHONG_DIR / "reference.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path} — run scripts/make_chong_fixtures.py")
    return json.loads(path.read_text(encoding="utf-8"))


def import_chong_test_molecules(project: QuantaProject) -> list[tuple[str, int]]:
    """Import ethane + hydrazine mol2 into the compound library and active project.

    Returns list of ``(name, compound_id)``.
    """
    ref = load_chong_reference()
    svc = CompoundService()
    imported: list[tuple[str, int]] = []
    for name in ("ethane", "hydrazine"):
        mol2 = CHONG_DIR / f"{name}.mol2"
        if not mol2.is_file():
            raise FileNotFoundError(f"Missing fixture {mol2}")
        meta = ref["molecules"][name]
        cid = svc.import_file(mol2, name=name, charge=0, multiplicity=1)
        obs = meta.get("chong_obs_ev") or {}
        bits = ", ".join(f"{k}≈{v} eV (obs)" for k, v in obs.items())
        label = f"{name} (Chong2007 {meta['formula']})"
        project_service.add_compound_to_project(project, cid, label=label)
        project = project_service.load_project(project.id)
        for entry in project.entries:
            if entry.compound_id == cid:
                entry.notes = (
                    f"Chong2007 Table 1: {bits}. "
                    "Smoke-test ΔSCF workflow (turn off C1s shift for gas-phase CEBE compare)."
                )
        project_service.save_project(project)
        imported.append((name, cid))
    return imported
