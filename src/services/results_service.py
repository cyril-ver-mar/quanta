"""L4 — curate Gaussian outputs and build XPS tables/spectra."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.core.xps import XpsSettings, apply_yamada_corrections, assign_core_levels, simulate_spectrum
from src.db.repositories import CompoundRepository, JobRepository
from src.services.gaussian_parser import parse_gaussian_log
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

    def curate_job(self, job_id: int, settings: AppSettings) -> dict:
        job = self.jobs.get(job_id)
        if job is None:
            raise ValueError("job not found")
        log_path = self.find_log(job_id)
        if log_path is None:
            raise FileNotFoundError(f"No log for job {job_id}")

        parsed = parse_gaussian_log(log_path)
        compound = self.compounds.get(job.compound_id)
        elements = (compound.meta_json or {}).get("elements") if compound else None

        levels = assign_core_levels(parsed.orbitals, element_counts=elements)
        xps_settings = XpsSettings(
            scale=settings.xps_scale,
            c1s_ref_ev=settings.xps_c1s_ref_ev,
            fwhm_ev=settings.xps_fwhm_ev,
            apply_linear_map=settings.xps_apply_linear_map,
            c1s_slope=settings.xps_c1s_slope,
            o1s_slope=settings.xps_o1s_slope,
            n1s_slope=settings.xps_n1s_slope,
        )
        levels = apply_yamada_corrections(levels, xps_settings)

        jdir = job_dir(job_id)
        curated = jdir / "curated"
        summary = {
            "job_id": job_id,
            "normal_termination": parsed.normal_termination,
            "method": parsed.method,
            "scf_energies_ha": parsed.scf_energies_ha,
            "opt_steps": parsed.opt_steps,
            "homo_ev": parsed.homo_ev,
            "lumo_ev": parsed.lumo_ev,
            "gap_ev": parsed.gap_ev,
            "n_orbitals": len(parsed.orbitals),
            "core_levels": [
                {
                    "element": lv.element,
                    "orbital_index": lv.orbital_index,
                    "energy_ha": lv.energy_ha,
                    "be_raw_ev": lv.binding_ev_raw,
                    "be_scaled_ev": lv.binding_ev_scaled,
                    "be_shifted_ev": lv.binding_ev_shifted,
                    "be_final_ev": lv.binding_ev_final,
                }
                for lv in levels
            ],
        }
        (curated / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        csv_path = curated / "core_levels.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "element",
                    "orbital_index",
                    "energy_ha",
                    "be_raw_ev",
                    "be_scaled_ev",
                    "be_shifted_ev",
                    "be_final_ev",
                ],
            )
            writer.writeheader()
            for row in summary["core_levels"]:
                writer.writerow(row)

        for element in ("C", "N", "O"):
            x, y = simulate_spectrum(levels, element, fwhm=settings.xps_fwhm_ev)
            if len(x) == 0:
                continue
            spec_path = curated / f"xps_{element}1s.csv"
            with spec_path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["binding_ev", "intensity"])
                for xi, yi in zip(x, y, strict=True):
                    w.writerow([f"{xi:.4f}", f"{yi:.6f}"])

        # convenience copy of log
        dest_log = jdir / "logs" / log_path.name
        if not dest_log.exists():
            dest_log.write_text(log_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

        logger.info("Curated job %s (%d core levels)", job_id, len(levels))
        return summary

    def load_summary(self, job_id: int) -> dict | None:
        path = job_dir(job_id) / "curated" / "summary.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
