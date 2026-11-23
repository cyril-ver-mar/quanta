"""Periodic GPAW ΔSCF: sites, charge convention, and a mocked full pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.engines.gpaw import (
    GpawSettings,
    ScfEnergy,
    calculator_keywords,
    charge_for_mode,
    gpaw_available,
    plan_gpaw_steps,
    referenced_delta,
    run_structure,
)
from src.core.periodic import inequivalent_sites, make_supercell, structure_from_arrays
from src.core.xps import simulate_spectrum


def _cn_layer() -> object:
    """Two equivalent C and two equivalent N in a flat cell."""
    return structure_from_arrays(
        ["C", "C", "N", "N"],
        [[1.0, 1.0, 5.0], [3.0, 1.0, 5.0], [1.0, 3.0, 5.0], [3.0, 3.0, 5.0]],
        [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 12.0]],
    )


def test_inequivalent_sites_group_equivalent_atoms() -> None:
    structure = _cn_layer()
    sites = inequivalent_sites(structure, elements=("C", "N"))
    by_element = {site.element: site for site in sites}
    assert set(by_element) == {"C", "N"}
    assert by_element["C"].multiplicity == 2
    assert by_element["N"].multiplicity == 2
    assert len(sites) == 2


def test_supercell_keeps_primitive_indices() -> None:
    structure = _cn_layer()
    super_cell = make_supercell(structure, (2, 1, 1))
    assert super_cell.n_atoms == 8
    assert super_cell.symbols[:4] == structure.symbols


def test_charge_modes_follow_the_gpaw_corehole_dataset() -> None:
    # Full 1s dataset already omits one core electron.
    # charge=-1 puts that electron back into the valence (neutral cell).
    assert charge_for_mode("neutral", 0) == -1
    # charge=0 leaves the electron out (ionized cell).
    assert charge_for_mode("charged", 0) == 0
    neutral = calculator_keywords(
        GpawSettings(charge_mode="neutral"),
        kind="corehole",
        atom_index=1,
        txt="core.txt",
    )
    assert neutral["charge"] == -1
    assert neutral["spinpol"] is True
    assert neutral["setups"] == {1: "fch1s"}
    assert neutral["occupations"]["fixmagmom"] is True
    assert neutral["occupations"]["name"] == "fermi-dirac"
    assert neutral["symmetry"]["point_group"] is False
    assert neutral["magmom"] == 1.0
    charged = calculator_keywords(
        GpawSettings(charge_mode="charged"),
        kind="corehole",
        atom_index=0,
        txt="core.txt",
    )
    assert charged["charge"] == 0
    assert "magmom" not in charged


def test_fermi_and_vbm_references() -> None:
    be, _note = referenced_delta(
        285.0,
        mode="fermi",
        charge_mode="neutral",
        fermi_ev=-5.0,
        vbm_ev=-6.0,
        cbm_ev=-4.0,
    )
    assert be == 285.0
    be_vbm, _note = referenced_delta(
        285.0,
        mode="vbm",
        charge_mode="neutral",
        fermi_ev=-5.0,
        vbm_ev=-6.0,
        cbm_ev=-4.0,
    )
    assert be_vbm == pytest.approx(287.0)
    be_charged, note = referenced_delta(
        290.0,
        mode="fermi",
        charge_mode="charged",
        fermi_ev=-4.0,
        vbm_ev=-6.0,
        cbm_ev=-1.0,
    )
    assert be_charged == pytest.approx(294.0)
    assert "background" in note


def test_missing_gpaw_explains_how_to_install() -> None:
    ok, message = gpaw_available()
    if ok:
        pytest.skip("GPAW is installed")
    assert "conda" in message
    assert "gpaw-setup" in message
    assert "core-hole" in message


def test_mocked_pipeline_produces_binding_energies_and_a_spectrum() -> None:
    structure = _cn_layer()
    settings = GpawSettings(
        charge_mode="neutral",
        reference_mode="absolute",
        elements=("C", "N"),
        supercell=(1, 1, 1),
    )
    calls: list[dict] = []

    def fake(_structure, keywords: dict) -> ScfEnergy:
        calls.append(keywords)
        if "setups" not in keywords:
            return ScfEnergy(
                total_ev=-1000.0,
                fermi_ev=-5.0,
                eigenvalues=[-12.0, -6.0, -3.0],
                occupations=[2.0, 2.0, 0.0],
            )
        index = next(iter(keywords["setups"]))
        element = _structure.symbols[index]
        shift = 286.0 if element == "C" else 398.5
        return ScfEnergy(total_ev=-1000.0 + shift, fermi_ev=-4.5)

    report = run_structure(structure, settings, evaluator=fake)
    assert len(calls) == 3  # ground state + C + N
    assert calls[0]["charge"] == 0
    assert calls[1]["charge"] == -1
    assert calls[2]["charge"] == -1
    by_element = {level.element: level for level in report.levels}
    assert by_element["C"].binding_ev_final == pytest.approx(286.0)
    assert by_element["N"].binding_ev_final == pytest.approx(398.5)
    assert by_element["C"].weight == 2
    x, y = simulate_spectrum(report.levels, "C", fwhm=1.2)
    assert len(x) > 10
    assert float(y.max()) > 1.5  # multiplicity 2

    steps, sites = plan_gpaw_steps(structure, settings, job_id=4)
    assert steps[0].kind.value == "neutral_sp"
    assert len(sites) == 2
    assert sum(step.weight for step in steps if step.kind.value == "corehole_sp") == 4


@pytest.fixture
def isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "test.db"
    jobs = tmp_path / "jobs"
    compounds = tmp_path / "compounds"
    jobs.mkdir()
    compounds.mkdir()
    monkeypatch.setattr("src.utils.paths.DB_PATH", db)
    monkeypatch.setattr("src.utils.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.utils.paths.JOBS_DIR", jobs)
    monkeypatch.setattr("src.utils.paths.CONFIG_PATH", tmp_path / "settings.json")
    monkeypatch.setattr("src.db.repositories.DB_PATH", db)
    monkeypatch.setattr("src.db.connection.DB_PATH", db)
    from src.utils.paths import ensure_runtime_dirs

    ensure_runtime_dirs()
    yield tmp_path


def test_job_queue_pipeline_with_fake_gpaw(isolated_data: Path) -> None:
    from src.core.models import Compound
    from src.core.periodic import element_counts, formula_from_symbols
    from src.db.repositories import CompoundRepository
    from src.services.gpaw_runner import GpawRunner
    from src.services.job_service import JobService
    from src.services.results_service import ResultsService
    from src.utils.config import AppSettings

    structure = _cn_layer()
    cid = CompoundRepository().add(
        Compound(
            id=None,
            name="cn-layer",
            source_format="extxyz",
            source_path=str(isolated_data / "cn.extxyz"),
            charge=0,
            multiplicity=1,
            formula=formula_from_symbols(structure.symbols),
            n_atoms=structure.n_atoms,
            meta_json={
                "periodic": True,
                "elements": element_counts(structure.symbols),
                "symbols": list(structure.symbols),
                "positions": [list(p) for p in structure.positions],
                "cell": [list(row) for row in structure.cell],
                "pbc": [True, True, True],
            },
        )
    )
    settings = AppSettings(engine="gpaw", xps_reference_mode="absolute", gpaw_charge_mode="neutral")
    job_id = JobService().create_job(cid, settings, name="cn-xps")
    script = next((isolated_data / "jobs").rglob("*.py"))
    text = script.read_text(encoding="utf-8")
    assert "GPAW" in text
    assert "FermiDirac" in text
    assert "PW(" in text

    def fake(_structure, keywords: dict) -> ScfEnergy:
        if "setups" not in keywords:
            return ScfEnergy(
                total_ev=-50.0,
                fermi_ev=-2.0,
                eigenvalues=[-8.0, -2.5, 1.0],
                occupations=[2.0, 2.0, 0.0],
            )
        index = next(iter(keywords["setups"]))
        shift = 285.0 if _structure.symbols[index] == "C" else 400.0
        return ScfEnergy(total_ev=-50.0 + shift)

    job = JobService().get(job_id)
    assert job is not None
    GpawRunner().run_job(job, settings, evaluator=fake)
    summary = ResultsService().load_summary(job_id)
    assert summary is not None
    assert summary["engine"] == "gpaw"
    finals = {row["element"]: row["be_final_ev"] for row in summary["core_levels"]}
    assert finals["C"] == pytest.approx(285.0)
    assert finals["N"] == pytest.approx(400.0)
    spec = (isolated_data / "jobs" / str(job_id) / "curated" / "xps_C1s.csv").read_text()
    assert "binding_ev" in spec
    assert len(spec.splitlines()) > 5
