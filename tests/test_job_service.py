"""Tests for ΔSCF job creation."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.dscf import StepKind, is_dscf_workflow
from src.core.models import Compound
from src.db.repositories import CompoundRepository
from src.services.job_service import JobService
from src.utils.config import AppSettings
from src.utils.paths import ensure_runtime_dirs


@pytest.fixture
def isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "test.db"
    compounds = tmp_path / "compounds"
    jobs = tmp_path / "jobs"
    compounds.mkdir()
    jobs.mkdir()
    monkeypatch.setattr("src.utils.paths.DB_PATH", db)
    monkeypatch.setattr("src.utils.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.utils.paths.JOBS_DIR", jobs)
    monkeypatch.setattr("src.db.repositories.DB_PATH", db)
    monkeypatch.setattr("src.db.connection.DB_PATH", db)
    ensure_runtime_dirs()
    yield tmp_path


def test_create_job_persists_workflow_steps(isolated_data: Path, tmp_path: Path) -> None:
    mol2 = tmp_path / "benzene.mol2"
    mol2.write_text(
        """@<TRIPOS>MOLECULE
benzene
 6 6 0 0 0
SMALL
NO_CHARGES

@<TRIPOS>ATOM
1 C 0.000 1.396 0.000 C.3 1 BENZ01 0.000
2 C 1.209 0.698 0.000 C.3 1 BENZ01 0.000
3 C 1.209 -0.698 0.000 C.3 1 BENZ01 0.000
4 C 0.000 -1.396 0.000 C.3 1 BENZ01 0.000
5 C -1.209 -0.698 0.000 C.3 1 BENZ01 0.000
6 C -1.209 0.698 0.000 C.3 1 BENZ01 0.000
@<TRIPOS>BOND
1 1 2 1
2 2 3 1
3 3 4 1
4 4 5 1
5 5 6 1
6 6 1 1
""",
        encoding="utf-8",
    )
    store = isolated_data / "compounds"
    dest = store / "benzene.mol2"
    dest.write_bytes(mol2.read_bytes())

    cid = CompoundRepository().add(
        Compound(
            id=None,
            name="benzene",
            source_format="mol2",
            source_path=str(dest),
            charge=0,
            multiplicity=1,
            formula="C6H6",
            n_atoms=6,
            meta_json={"elements": {"C": 6, "H": 6}},
        )
    )

    settings = AppSettings.load()
    jid = JobService().create_job(cid, settings)
    steps = JobService().get_steps(jid)

    assert is_dscf_workflow(steps)
    assert steps[0].kind == StepKind.OPT
    assert any(s.kind == StepKind.NEUTRAL_SP for s in steps)
    assert len(steps) >= 2

    from src.utils.paths import job_dir

    gjf = job_dir(jid) / "input" / steps[0].gjf_name
    text = gjf.read_text(encoding="utf-8")
    assert "geom=connectivity" in text
    assert any(line.startswith("1 ") and "2 " in line for line in text.splitlines())
