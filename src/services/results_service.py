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
            n1s_ref_ev=settings.xps_n1s_ref_ev,
            o1s_ref_ev=settings.xps_o1s_ref_ev,
            apply_c1s_shift=settings.dscf_apply_c1s_shift,
            reference_mode=settings.xps_reference_mode,
            reference_element=settings.xps_reference_element,
        )

    def _resolve_step_log(self, job_id: int, log_name: str, gaussian_cwd: str | None) -> Path | None:
        """Prefer job raw/, then Gaussian work dir (case-insensitive stem match)."""
        jdir = job_dir(job_id)
        raw = jdir / "raw" / log_name
        if raw.is_file() and raw.stat().st_size > 0:
            return raw
        # Case variants on Windows
        stem = Path(log_name).stem
        for pat in (f"{stem}.log", f"{stem}.LOG", f"{stem}.out", f"{stem}.OUT"):
            cand = jdir / "raw" / pat
            if cand.is_file() and cand.stat().st_size > 0:
                return cand
        if gaussian_cwd:
            cwd = Path(gaussian_cwd)
            if cwd.is_dir():
                for pat in (f"{stem}.log", f"{stem}.LOG", f"{stem}.out", f"{stem}.OUT"):
                    cand = cwd / pat
                    if cand.is_file() and cand.stat().st_size > 0:
                        return cand
        return None

    def curate_job(self, job_id: int, settings: AppSettings) -> dict:
        job = self.jobs.get(job_id)
        if job is None:
            raise ValueError("job not found")

        if (job.meta_json or {}).get("engine") == "gpaw":
            return self._curate_gpaw(job, settings)

        steps = deserialize_steps(job.meta_json.get("steps") or [])
        neutral = next((s for s in steps if s.kind == StepKind.NEUTRAL_SP), None)
        if neutral is None:
            raise ValueError("Not a ΔSCF workflow job")

        gauss_cwd = (job.meta_json or {}).get("gaussian_cwd")
        neutral_log = self._resolve_step_log(job_id, neutral.log_name, gauss_cwd)
        if neutral_log is None:
            raise FileNotFoundError(f"Neutral SP log missing: {neutral.log_name}")

        neutral_parsed = parse_gaussian_log(neutral_log)
        e0 = final_scf_energy_ha(neutral_parsed)
        if e0 is None and neutral.energy_ha is not None:
            e0 = float(neutral.energy_ha)
        if e0 is None:
            raise ValueError("Could not read E₀ from neutral SP log")

        corehole_data: list[tuple[int, str, float]] = []
        skipped: list[str] = []
        for step in steps:
            if step.kind != StepKind.COREHOLE_SP:
                continue
            if step.status != StepStatus.COMPLETED:
                skipped.append(f"{step.key}: status={step.status.value}")
                continue
            if step.atom_index is None or step.element is None:
                skipped.append(f"{step.key}: missing atom map")
                continue

            e_i: float | None = None
            log_path = self._resolve_step_log(job_id, step.log_name, gauss_cwd)
            if log_path is not None:
                parsed = parse_gaussian_log(log_path)
                e_i = final_scf_energy_ha(parsed)
            if e_i is None and step.energy_ha is not None:
                e_i = float(step.energy_ha)
            if e_i is None:
                skipped.append(
                    f"{step.key}: no SCF energy "
                    f"(log={'missing' if log_path is None else log_path.name})"
                )
                continue
            if log_path is not None and e0 is not None:
                from src.core.dscf import HA_TO_EV, corehole_charge_multiplicity
                from src.core.gaussian_mos import assess_core_hole, parse_population

                compound = self.compounds.get(job.compound_id)
                multiplicity = 2
                if compound is not None:
                    _charge, multiplicity = corehole_charge_multiplicity(
                        compound.charge, compound.multiplicity
                    )
                verdict = assess_core_hole(
                    element=step.element,
                    atom_index=step.atom_index,
                    multiplicity=multiplicity,
                    be_raw_ev=(e_i - e0) * HA_TO_EV,
                    population=parse_population(
                        log_path.read_text(encoding="utf-8", errors="replace")
                    ),
                )
                if not verdict.ok:
                    skipped.append(f"{step.key}: {verdict.message}")
                    continue
            corehole_data.append((step.atom_index, step.element, e_i))

        if skipped:
            logger.warning(
                "Job %s curation skipped %d core-hole step(s): %s",
                job_id,
                len(skipped),
                "; ".join(skipped),
            )

        dscf = self._dscf_settings(settings)
        reference_info: dict = {}
        levels = compute_binding_energies(
            e0,
            corehole_data,
            c1s_ref_ev=dscf.c1s_ref_ev,
            n1s_ref_ev=dscf.n1s_ref_ev,
            o1s_ref_ev=dscf.o1s_ref_ev,
            apply_c1s_shift=dscf.apply_c1s_shift,
            reference_mode=dscf.reference_mode,
            reference_element=dscf.reference_element,
            info=reference_info,
        )

        opt = next((s for s in steps if s.kind == StepKind.OPT), None)
        opt_log = (
            self._resolve_step_log(job_id, opt.log_name, gauss_cwd) if opt else None
        )
        homo_ev = lumo_ev = gap_ev = None
        opt_steps = None
        if opt_log is not None:
            opt_parsed = parse_gaussian_log(opt_log)
            homo_ev = opt_parsed.homo_ev
            lumo_ev = opt_parsed.lumo_ev
            gap_ev = opt_parsed.gap_ev
            opt_steps = opt_parsed.opt_steps
        # Neutral SP usually has Pop eigenvalues; fall back if OPT has none
        if homo_ev is None:
            homo_ev = neutral_parsed.homo_ev
            lumo_ev = neutral_parsed.lumo_ev
            gap_ev = neutral_parsed.gap_ev

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
            "engine": "gaussian",
            "n_corehole_jobs": len(corehole_data),
            "curation_skipped": skipped,
            "reference": reference_info,
            "core_levels": [
                {
                    "element": lv.element,
                    "atom_index": lv.atom_index,
                    "be_raw_ev": lv.binding_ev_raw,
                    "be_shifted_ev": lv.binding_ev_shifted,
                    "be_final_ev": lv.binding_ev_final,
                    "weight": lv.weight,
                    "reference_mode": lv.reference_mode,
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
                fieldnames=[
                    "element",
                    "atom_index",
                    "be_raw_ev",
                    "be_shifted_ev",
                    "be_final_ev",
                    "weight",
                    "reference_mode",
                ],
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

    def _curate_gpaw(self, job, settings: AppSettings) -> dict:
        from src.core.engines.gpaw import GpawSettings, HoleEnergy, build_levels

        steps = deserialize_steps(job.meta_json.get("steps") or [])
        ground = (job.meta_json or {}).get("gpaw_ground_state") or {}
        e0 = ground.get("e0_ev")
        neutral = next((s for s in steps if s.kind == StepKind.NEUTRAL_SP), None)
        if e0 is None and neutral is not None and neutral.energy_ev is not None:
            e0 = neutral.energy_ev
        if e0 is None:
            raise ValueError("Could not read the GPAW ground-state energy E₀")

        holes: list[HoleEnergy] = []
        skipped: list[str] = []
        for step in steps:
            if step.kind != StepKind.COREHOLE_SP:
                continue
            if step.status != StepStatus.COMPLETED or step.energy_ev is None:
                skipped.append(f"{step.key}: status={step.status.value}")
                continue
            holes.append(
                HoleEnergy(
                    atom_index=int(step.atom_index or 0),
                    element=step.element or "",
                    multiplicity=int(step.weight or 1),
                    energy_ev=float(step.energy_ev),
                )
            )
        gpaw = GpawSettings.from_app(settings, base_charge=0)
        stored_mode = (job.meta_json or {}).get("charge_mode")
        if stored_mode:
            gpaw.charge_mode = str(stored_mode)
        report = build_levels(
            e0_ev=float(e0),
            holes=holes,
            settings=gpaw,
            fermi_ev=ground.get("fermi_ev"),
            vbm_ev=ground.get("vbm_ev"),
            cbm_ev=ground.get("cbm_ev"),
        )
        jdir = job_dir(job.id)
        curated = jdir / "curated"
        curated.mkdir(parents=True, exist_ok=True)
        summary = {
            "job_id": job.id,
            "protocol": "dscf",
            "engine": "gpaw",
            "e0_ev": report.e0_ev,
            "e0_ha": None,
            "method": f"GPAW {gpaw.xc}",
            "charge_mode": report.charge_mode,
            "fermi_ev": report.fermi_ev,
            "vbm_ev": report.vbm_ev,
            "cbm_ev": report.cbm_ev,
            "n_corehole_jobs": len(holes),
            "curation_skipped": skipped,
            "reference": report.reference,
            "notes": report.notes,
            "core_levels": [
                {
                    "element": lv.element,
                    "atom_index": lv.atom_index,
                    "be_raw_ev": lv.binding_ev_raw,
                    "be_shifted_ev": lv.binding_ev_shifted,
                    "be_final_ev": lv.binding_ev_final,
                    "weight": lv.weight,
                    "reference_mode": lv.reference_mode,
                }
                for lv in report.levels
            ],
            "workflow_steps": [s.to_dict() for s in steps],
        }
        (curated / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        csv_path = curated / "core_levels.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "element",
                    "atom_index",
                    "be_raw_ev",
                    "be_shifted_ev",
                    "be_final_ev",
                    "weight",
                    "reference_mode",
                ],
            )
            writer.writeheader()
            for row in summary["core_levels"]:
                writer.writerow(row)
        for element in ("C", "N", "O"):
            x, y = simulate_spectrum(report.levels, element, fwhm=gpaw.fwhm_ev)
            if len(x) == 0:
                continue
            spec_path = curated / f"xps_{element}1s.csv"
            with spec_path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["binding_ev", "intensity"])
                for xi, yi in zip(x, y, strict=True):
                    w.writerow([f"{xi:.4f}", f"{yi:.6f}"])
        logger.info("Curated GPAW job %s (%d peaks)", job.id, len(report.levels))
        return summary

    def load_summary(self, job_id: int) -> dict | None:
        path = job_dir(job_id) / "curated" / "summary.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
