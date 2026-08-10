"""L4 — create and manage calculation jobs."""

from __future__ import annotations

from pathlib import Path

from src.core.gaussian_input import DEFAULT_ROUTE
from src.core.models import Job, JobStatus
from src.db.repositories import JobRepository
from src.services.compound_service import CompoundService
from src.utils.config import AppSettings
from src.utils.logging_setup import get_logger
from src.utils.paths import job_dir

logger = get_logger("quanta.jobs")


class JobService:
    def __init__(self) -> None:
        self.repo = JobRepository()
        self.compounds = CompoundService()

    def create_job(self, compound_id: int, settings: AppSettings, name: str | None = None) -> int:
        compound = self.compounds.get(compound_id)
        if compound is None:
            raise ValueError(f"Compound {compound_id} not found")
        job = Job(
            id=None,
            compound_id=compound_id,
            name=name or f"{compound.name}_opt_xps",
            status=JobStatus.QUEUED,
            route=DEFAULT_ROUTE,
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
        )
        job_id = self.repo.add(job)
        jdir = job_dir(job_id)
        gjf = self.compounds.build_gjf_text(
            compound,
            nproc=settings.nproc,
            mem_mb=settings.mem_mb,
            chk_name=f"job_{job_id}.chk",
        )
        input_path = jdir / "input" / f"job_{job_id}.gjf"
        input_path.write_text(gjf, encoding="utf-8")
        # also copy source structure
        src = Path(compound.source_path)
        if src.exists():
            (jdir / "input" / src.name).write_bytes(src.read_bytes())
        job = self.repo.get(job_id)
        assert job is not None
        job.work_path = str(jdir)
        job.meta_json["gjf"] = str(input_path)
        self.repo.update(job)
        logger.info("Created job %s for compound %s", job_id, compound_id)
        return job_id

    def list_jobs(self) -> list[Job]:
        return self.repo.list_all()

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
        job.status = JobStatus.QUEUED
        job.error = ""
        job.progress = 0.0
        self.repo.update(job)

    def pause_queue(self) -> None:
        for job in self.repo.list_by_status(JobStatus.QUEUED):
            job.status = JobStatus.PAUSED
            self.repo.update(job)

    def resume_queue(self) -> None:
        for job in self.repo.list_by_status(JobStatus.PAUSED):
            job.status = JobStatus.QUEUED
            self.repo.update(job)
