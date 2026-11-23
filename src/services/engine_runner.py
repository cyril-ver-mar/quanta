"""Pick the XPS engine for the next queued job.

Gaussian and GPAW share the job queue. An ORCA runner would be another branch.
"""

from __future__ import annotations

from src.core.engines.gpaw import gpaw_available
from src.core.models import JobStatus
from src.db.repositories import JobRepository
from src.services.gaussian_runner import GaussianRunner, gaussian_available
from src.services.gpaw_runner import GpawRunner
from src.utils.config import AppSettings


def run_next(settings: AppSettings) -> int | None:
    """Run the next queued job whose engine is available on this machine."""
    queued = JobRepository().list_by_status(JobStatus.QUEUED)
    if not queued:
        return None
    for job in queued:
        engine = (job.meta_json or {}).get("engine", "gaussian")
        if engine == "gpaw":
            ok, message = gpaw_available()
            if not ok:
                job.status = JobStatus.FAILED
                job.error = message
                JobRepository().update(job)
                continue
            return GpawRunner().run_next(settings)
        if gaussian_available(settings):
            return GaussianRunner().run_next(settings)
        continue
    return None


def queue_can_run(settings: AppSettings) -> tuple[bool, str]:
    """Whether the Queue 'run' button has an engine it can launch."""
    queued = JobRepository().list_by_status(JobStatus.QUEUED)
    engines = {(job.meta_json or {}).get("engine", "gaussian") for job in queued}
    if not engines:
        engines = {(getattr(settings, "engine", None) or "gaussian")}
    messages: list[str] = []
    if "gaussian" in engines and gaussian_available(settings):
        return True, ""
    if "gaussian" in engines:
        messages.append("Gaussian executable was not found.")
    if "gpaw" in engines:
        ok, message = gpaw_available()
        if ok:
            return True, ""
        messages.append(message)
    if not messages:
        messages.append("No XPS engine is available for the queued jobs.")
    return False, " ".join(messages)
