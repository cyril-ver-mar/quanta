"""L4 — curate Gaussian ΔSCF outputs and build XPS tables/spectra."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.core.dscf import (
    DscfSettings,
    StepKind,
    StepStatus,
    compute_binding_energies,
    deserialize_steps,
)
from src.core.xps import simulate_spectrum
from src.db.repositories import CompoundRepository, JobRepository
from src.services.gaussian_parser import final_scf_energy_ha, parse_gaussian_log
from src.utils.config import AppSettings
from src.utils.logging_setup import get_logger
from src.utils.paths import job_dir

logger = get_logger("quanta.results")


class ResultsService:
    def __init__(self) -> None:
        self.jobs = JobRepository()
        self.compounds = CompoundRepository()

    def find_log(self, job_id: int) -> Path | None:
        jdir = job_dir(job_id)
        candidates = list((jdir / "raw").glob("*.log")) + list((jdir / "raw").glob("*.LOG"))
        candidates += list((jdir / "logs").glob("*.log"))
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def _dscf_settings(self, settings: AppSettings) -> DscfSettings:
        return DscfSettings(
            functional=settings.dscf_functional,
            basis=settings.dscf_basis,
            fwhm_ev=settings.xps_fwhm_ev,
            c1s_ref_ev=settings.xps_c1s_ref_ev,
            apply_c1s_shift=settings.dscf_apply_c1s_shift,
        )

    def curate_job(self, job_id: int, settings: AppSettings) -> dict:
        job = self.jobs.get(job_id)
        if job is None:
            raise ValueError("job not found")

        steps = deserialize_steps(job.meta_json.get("steps") or [])
        neutral = next((s for s in steps if s.kind == StepKind.NEUTRAL_SP), None)
        if neutral is None:
            raise ValueError("Not a ΔSCF workflow job")

        neutral_log = job_dir(job_id) / "raw" / neutral.log_name
        if not neutral_log.exists():
            raise FileNotFoundError(f"Neutral SP log missing: {neutral_log}")

        neutral_parsed = parse_gaussian_log(neutral_log)
        e0 = final_scf_energy_ha(neutral_parsed)
        if e0 is None:
            raise ValueError("Could not read E₀ from neutral SP log")

        corehole_data: list[tuple[int, str, float]] = []
        for step in steps:
            if step.kind != StepKind.COREHOLE_SP or step.status != StepStatus.COMPLETED:
                continue
            log_path = job_dir(job_id) / "raw" / step.log_name
            if not log_path.exists():
                continue
            parsed = parse_gaussian_log(log_path)
            e_i = final_scf_energy_ha(parsed)
            if e_i is None or step.atom_index is None or step.element is None:
                continue
            corehole_data.append((step.atom_index, step.element, e_i))

        dscf = self._dscf_settings(settings)
        levels = compute_binding_energies(
            e0,
            corehole_data,
            c1s_ref_ev=dscf.c1s_ref_ev,
            apply_c1s_shift=dscf.apply_c1s_shift,
        )

        opt = next((s for s in steps if s.kind == StepKind.OPT), None)
        opt_log = job_dir(job_id) / "raw" / opt.log_name if opt else None
        homo_ev = lumo_ev = gap_ev = None
        opt_steps = None
        if opt_log and opt_log.exists():
            opt_parsed = parse_gaussian_log(opt_log)
            homo_ev = opt_parsed.homo_ev
            lumo_ev = opt_parsed.lumo_ev
            gap_ev = opt_parsed.gap_ev
            opt_steps = opt_parsed.opt_steps

        jdir = job_dir(job_id)
        curated = jdir / "curated"
        curated.mkdir(parents=True, exist_ok=True)

        summary = {
            "job_id": job_id,
            "protocol": "dscf",
            "e0_ha": e0,
            "normal_termination": neutral_parsed.normal_termination,
            "method": f"{dscf.functional}/{dscf.basis}",
            "opt_steps": opt_steps,
            "homo_ev": homo_ev,
            "lumo_ev": lumo_ev,
            "gap_ev": gap_ev,
            "n_corehole_jobs": len(corehole_data),
            "core_levels": [
                {
                    "element": lv.element,
                    "atom_index": lv.atom_index,
                    "be_raw_ev": lv.binding_ev_raw,
                    "be_shifted_ev": lv.binding_ev_shifted,
                    "be_final_ev": lv.binding_ev_final,
                }
                for lv in levels
            ],
            "workflow_steps": [s.to_dict() for s in steps],
        }
        (curated / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        csv_path = curated / "core_levels.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["element", "atom_index", "be_raw_ev", "be_shifted_ev", "be_final_ev"],
            )
            writer.writeheader()
            for row in summary["core_levels"]:
                writer.writerow(row)

        for element in ("C", "N", "O"):
            x, y = simulate_spectrum(levels, element, fwhm=dscf.fwhm_ev)
            if len(x) == 0:
                continue
            spec_path = curated / f"xps_{element}1s.csv"
            with spec_path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["binding_ev", "intensity"])
                for xi, yi in zip(x, y, strict=True):
                    w.writerow([f"{xi:.4f}", f"{yi:.6f}"])

        logger.info("Curated ΔSCF job %s (%d peaks)", job_id, len(levels))
        return summary

    def load_summary(self, job_id: int) -> dict | None:
        path = job_dir(job_id) / "curated" / "summary.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
