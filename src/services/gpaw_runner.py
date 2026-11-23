"""Run a periodic ΔSCF workflow with GPAW. GPAW is imported only when a job runs."""

from __future__ import annotations

from typing import Callable

from src.core.dscf import StepKind, StepStatus, next_runnable_step
from src.core.engines.gpaw import (
    GpawSettings,
    ScfEnergy,
    band_edges,
    calculator_keywords,
    gpaw_available,
)
from src.core.models import Job, JobStatus
from src.core.periodic import make_supercell, structure_from_arrays
from src.db.repositories import JobRepository
from src.services.job_service import JobService
from src.services.results_service import ResultsService
from src.utils.config import AppSettings
from src.utils.logging_setup import get_logger
from src.utils.paths import job_dir

logger = get_logger("quanta.gpaw")

Evaluator = Callable[[object, dict], ScfEnergy]


class GpawRunner:
    def __init__(self) -> None:
        self.repo = JobRepository()
        self.jobs = JobService()
        self.results = ResultsService()

    def run_next(self, settings: AppSettings, evaluator: Evaluator | None = None) -> int | None:
        queued = self.repo.list_by_status(JobStatus.QUEUED)
        for candidate in queued:
            if (candidate.meta_json or {}).get("engine") != "gpaw":
                continue
            return self.run_job(candidate, settings, evaluator=evaluator)
        return None

    def run_job(
        self,
        job: Job,
        settings: AppSettings,
        evaluator: Evaluator | None = None,
    ) -> int | None:
        if job.id is None:
            return None
        if evaluator is None:
            ok, message = gpaw_available()
            if not ok:
                job.status = JobStatus.FAILED
                job.error = message
                self.repo.update(job)
                return job.id
            evaluator = _gpaw_evaluator
        job.status = JobStatus.RUNNING
        self.repo.update(job)
        try:
            self._run_steps(job.id, settings, evaluator)
        except Exception as exc:
            logger.exception("GPAW job %s failed", job.id)
            job = self.repo.get(job.id)
            if job:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                self.repo.update(job)
            return job.id
        return job.id

    def _run_steps(self, job_id: int, settings: AppSettings, evaluator: Evaluator) -> None:
        job = self.repo.get(job_id)
        assert job is not None
        spec = (job.meta_json or {}).get("gpaw") or {}
        raw = spec.get("structure") or {}
        primitive = structure_from_arrays(
            list(raw["symbols"]),
            raw["positions"],
            raw["cell"],
            raw.get("pbc") or (True, True, True),
        )
        repeat = tuple(int(x) for x in (spec.get("supercell") or [1, 1, 1]))
        structure = make_supercell(primitive, repeat)  # type: ignore[arg-type]
        gpaw = GpawSettings.from_app(settings, base_charge=0)
        if spec.get("charge_mode"):
            gpaw.charge_mode = str(spec["charge_mode"])
        jdir = job_dir(job_id)

        while True:
            steps = self.jobs.get_steps(job_id)
            step = next_runnable_step(steps)
            if step is None:
                break
            step.status = StepStatus.RUNNING
            self._replace(job_id, step)
            kind = "neutral" if step.kind == StepKind.NEUTRAL_SP else "corehole"
            keywords = calculator_keywords(
                gpaw,
                kind=kind,
                atom_index=step.atom_index,
                txt=str(jdir / "raw" / step.log_name),
            )
            keywords["setup_dir"] = gpaw.setup_dir
            result = evaluator(structure, keywords)
            step.energy_ev = float(result.total_ev)
            step.status = StepStatus.COMPLETED
            step.error = ""
            if step.kind == StepKind.NEUTRAL_SP:
                vbm, cbm = band_edges(result.eigenvalues, result.occupations)
                job = self.repo.get(job_id)
                assert job is not None
                job.meta_json["gpaw_ground_state"] = {
                    "e0_ev": float(result.total_ev),
                    "fermi_ev": result.fermi_ev,
                    "vbm_ev": vbm,
                    "cbm_ev": cbm,
                    "eigenvalues": result.eigenvalues,
                    "occupations": result.occupations,
                }
                self.repo.update(job)
                self._replace(job_id, step)
                self._queue_coreholes(job_id)
            else:
                self._replace(job_id, step)

        steps = self.jobs.get_steps(job_id)
        job = self.repo.get(job_id)
        assert job is not None
        failed = [s for s in steps if s.status == StepStatus.FAILED]
        waiting = [s for s in steps if s.status in (StepStatus.WAITING, StepStatus.QUEUED, StepStatus.RUNNING)]
        if waiting:
            job.status = JobStatus.QUEUED
        elif failed:
            job.status = JobStatus.FAILED
            job.error = "; ".join(s.error for s in failed if s.error)[:2000]
        else:
            job.status = JobStatus.COMPLETED
        self.repo.update(job)
        if not waiting:
            self.results.curate_job(job_id, settings)

    def _queue_coreholes(self, job_id: int) -> None:
        steps = self.jobs.get_steps(job_id)
        for step in steps:
            if step.kind == StepKind.COREHOLE_SP and step.status == StepStatus.WAITING:
                step.status = StepStatus.QUEUED
        self.jobs.save_steps(job_id, steps)

    def _replace(self, job_id: int, step) -> None:
        steps = self.jobs.get_steps(job_id)
        for i, current in enumerate(steps):
            if current.key == step.key:
                steps[i] = step
        self.jobs.save_steps(job_id, steps)


def _gpaw_evaluator(structure, keywords: dict) -> ScfEnergy:
    """One GPAW total energy, using the documented calculator arguments."""
    ok, message = gpaw_available()
    if not ok:
        raise ImportError(message)
    from ase import Atoms
    from gpaw import GPAW, PW, FermiDirac, setup_paths

    setup_dir = keywords.get("setup_dir") or ""
    if setup_dir and setup_dir not in setup_paths:
        setup_paths.insert(0, setup_dir)
    atoms = Atoms(
        symbols=list(structure.symbols),
        positions=[list(p) for p in structure.positions],
        cell=[list(row) for row in structure.cell],
        pbc=list(structure.pbc),
    )
    if keywords.get("magmom_atom") is not None:
        atoms[int(keywords["magmom_atom"])].magmom = float(keywords["magmom"])
    occ = keywords["occupations"]
    fermi_kwargs = {"fixmagmom": True} if occ.get("fixmagmom") else {}
    gkwargs = {
        "mode": PW(float(keywords["mode"]["cutoff_ev"])),
        "xc": keywords["xc"],
        "kpts": tuple(keywords["kpts"]),
        "charge": int(keywords["charge"]),
        "txt": keywords.get("txt") or "-",
        "occupations": FermiDirac(float(occ["width_ev"]), **fermi_kwargs),
    }
    if keywords.get("spinpol"):
        gkwargs["spinpol"] = True
    if keywords.get("setups"):
        gkwargs["setups"] = dict(keywords["setups"])
    if keywords.get("symmetry"):
        gkwargs["symmetry"] = dict(keywords["symmetry"])
    calc = GPAW(**gkwargs)
    atoms.calc = calc
    total = float(atoms.get_potential_energy()) + float(calc.get_reference_energy())
    fermi = float(calc.get_fermi_level())
    nspins = int(calc.get_number_of_spins()) if hasattr(calc, "get_number_of_spins") else 1
    eigenvalues: list[float] = []
    occupations: list[float] = []
    for spin in range(max(nspins, 1)):
        eigenvalues.extend(float(v) for v in calc.get_eigenvalues(kpt=0, spin=spin))
        occupations.extend(float(v) for v in calc.get_occupation_numbers(kpt=0, spin=spin))
    return ScfEnergy(
        total_ev=total,
        fermi_ev=fermi,
        eigenvalues=eigenvalues,
        occupations=occupations,
    )

