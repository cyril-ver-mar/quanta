"""L4 — create and manage ΔSCF calculation workflows."""

from __future__ import annotations

from pathlib import Path

from src.core.dscf import (
    DscfSettings,
    DscfStep,
    StepKind,
    StepStatus,
    build_workflow_steps,
    opt_route,
    serialize_steps,
)
from src.core.gaussian_input import (
    GaussianJobSpec,
    connectivity_from_mol,
    write_checkpoint_job,
    write_gjf,
)
from src.core.models import Job, JobStatus
from src.db.repositories import JobRepository
from src.services.compound_service import CompoundService, mol_to_atoms
from src.utils.config import AppSettings
from src.utils.logging_setup import get_logger
from src.utils.paths import job_dir

logger = get_logger("quanta.jobs")


class JobService:
    def __init__(self) -> None:
        self.repo = JobRepository()
        self.compounds = CompoundService()

    def _dscf_settings(self, settings: AppSettings) -> DscfSettings:
        return DscfSettings(
            functional=settings.dscf_functional,
            basis=settings.dscf_basis,
            fwhm_ev=settings.xps_fwhm_ev,
            c1s_ref_ev=settings.xps_c1s_ref_ev,
            apply_c1s_shift=settings.dscf_apply_c1s_shift,
        )

    def create_job(
        self,
        compound_id: int,
        settings: AppSettings,
        name: str | None = None,
        *,
        project_name: str | None = None,
    ) -> int:
        compound = self.compounds.get(compound_id)
        if compound is None:
            raise ValueError(f"Compound {compound_id} not found")

        dscf = self._dscf_settings(settings)
        proj = (project_name or "default").strip() or "default"
        job = Job(
            id=None,
            compound_id=compound_id,
            name=name or f"{compound.name}_dscf_xps",
            status=JobStatus.QUEUED,
            route=opt_route(dscf),
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
            meta_json={"protocol": "dscf", "project_name": proj},
        )
        job_id = self.repo.add(job)
        jdir = job_dir(job_id)
        mol = self.compounds.load_molecule(compound)
        atoms = mol_to_atoms(mol)
        steps = build_workflow_steps(atoms, dscf, job_id)
        opt = steps[0]
        opt_gjf = jdir / "input" / opt.gjf_name
        connectivity = connectivity_from_mol(mol) if mol.GetNumBonds() > 0 else None
        spec = GaussianJobSpec(
            title=f"{compound.name} - DSCF step 1 OPT",
            charge=compound.charge,
            multiplicity=compound.multiplicity,
            atoms=atoms,
            connectivity=connectivity,
            chk_name=f"job_{job_id}_opt.chk",
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
            route=opt.route,
        )
        opt_gjf.write_text(write_gjf(spec), encoding="utf-8")

        src = Path(compound.source_path)
        if src.exists():
            (jdir / "input" / src.name).write_bytes(src.read_bytes())

        job = self.repo.get(job_id)
        assert job is not None
        job.work_path = str(jdir)
        job.meta_json["steps"] = serialize_steps(steps)
        job.meta_json["total_steps"] = len(steps)
        job.meta_json["current_gjf"] = str(opt_gjf)
        self.repo.update(job)
        logger.info("Created ΔSCF workflow job %s (%d steps)", job_id, len(steps))
        return job_id

    def get_steps(self, job_id: int) -> list[DscfStep]:
        job = self.repo.get(job_id)
        if job is None:
            return []
        from src.core.dscf import deserialize_steps

        return deserialize_steps(job.meta_json.get("steps") or [])

    def save_steps(self, job_id: int, steps: list[DscfStep]) -> None:
        job = self.repo.get(job_id)
        if job is None:
            return
        job.meta_json["steps"] = serialize_steps(steps)
        job.progress = sum(1 for s in steps if s.status == StepStatus.COMPLETED) / max(len(steps), 1)
        self.repo.update(job)

    def write_neutral_gjf(self, job_id: int, settings: AppSettings) -> Path:
        job = self.repo.get(job_id)
        compound = self.compounds.get(job.compound_id) if job else None
        if job is None or compound is None:
            raise ValueError("job/compound missing")
        steps = self.get_steps(job_id)
        neutral = next(s for s in steps if s.kind == StepKind.NEUTRAL_SP)
        jdir = job_dir(job_id)
        text = write_checkpoint_job(
            title=f"{compound.name} - DSCF step 2 neutral SP",
            charge=compound.charge,
            multiplicity=compound.multiplicity,
            route=neutral.route,
            oldchk=f"job_{job_id}_opt.chk",
            chk=f"job_{job_id}_neutral.chk",
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
        )
        path = jdir / "input" / neutral.gjf_name
        path.write_text(text, encoding="utf-8")
        return path

    def write_corehole_gjf(
        self,
        job_id: int,
        step: DscfStep,
        settings: AppSettings,
    ) -> Path:
        job = self.repo.get(job_id)
        compound = self.compounds.get(job.compound_id) if job else None
        if job is None or compound is None:
            raise ValueError("job/compound missing")
        if step.orbital_index is None or step.homo_index is None:
            raise ValueError(f"Orbital mapping missing for step {step.key}")
        label = f"{step.element}{step.atom_index + 1}"
        text = write_checkpoint_job(
            title=f"{compound.name} - DSCF core hole {label}",
            charge=compound.charge,
            multiplicity=2,
            route=step.route,
            oldchk=f"job_{job_id}_neutral.chk",
            chk=f"job_{job_id}_corehole_{label}.chk",
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
            alter_swap=(step.orbital_index, step.homo_index),
        )
        path = job_dir(job_id) / "input" / step.gjf_name
        path.write_text(text, encoding="utf-8")
        return path

    def list_jobs(self) -> list[Job]:
        return self.repo.list_all()

    def list_jobs_for_compounds(self, compound_ids: list[int]) -> list[Job]:
        return self.repo.list_by_compound_ids(compound_ids)

    def get(self, job_id: int) -> Job | None:
        return self.repo.get(job_id)

    def set_status(self, job_id: int, status: JobStatus, error: str = "") -> None:
        job = self.repo.get(job_id)
        if job is None:
            return
        job.status = status
        if error:
            job.error = error
        self.repo.update(job)

    def delete_pending(self, job_id: int) -> None:
        self.repo.delete_pending(job_id)

    def restart_failed(self, job_id: int) -> None:
        job = self.repo.get(job_id)
        if job is None:
            return
        if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.COMPLETED):
            raise ValueError("Only failed/cancelled/completed jobs can be re-queued")
        steps = self.get_steps(job_id)
        job.status = JobStatus.QUEUED
        job.error = ""
        job.progress = 0.0
        for i, step in enumerate(steps):
            step.energy_ha = None
            step.error = ""
            step.orbital_index = None
            step.homo_index = None
            step.status = StepStatus.QUEUED if i == 0 else StepStatus.WAITING
        job.meta_json["steps"] = serialize_steps(steps)
        self.repo.update(job)

    def pause_queue(self) -> None:
        for job in self.repo.list_by_status(JobStatus.QUEUED):
            job.status = JobStatus.PAUSED
            self.repo.update(job)

    def resume_queue(self) -> None:
        for job in self.repo.list_by_status(JobStatus.PAUSED):
            job.status = JobStatus.QUEUED
            self.repo.update(job)
