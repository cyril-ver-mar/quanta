# Changelog

All notable changes to this project are listed here.  
Version source of truth: root `VERSION`. Git tags: `vMAJOR.MINOR.PATCH`.

## [Unreleased]

## [1.0.2] — 2026-08-22

### Added
- XPS-Deconv-style **install.sh** / **install.bat** with 6-step UX, error hints, and import smoke-test.
- `src/utils/deps_check.py` and `requirements-runtime.txt` (runtime deps without pytest).
- `standalone/Quanta/` folder with install scripts and user README for distributable builds.

## [1.0.1] — 2026-08-22

### Added
- **ΔSCF XPS workflow** (gas phase, Gaussian 09): OPT → neutral SP (E₀) → core-hole SP per C/N/O atom (`Guess=Alter`).
- Step-by-step workflow UI on Jobs, Queue, and Results (EN/RU).
- Work Review page with 3D structure preview (py3Dmol).
- Settings: PBE/B3LYP functional, basis, Voigt FWHM, optional C1s shift.

### Changed
- Replaced Yamada orbital-energy XPS pipeline with ΔSCF binding energies (BE = ΔE).
- Job runner executes multi-step workflows sequentially; results curation from core-hole logs.

### Notes
- Yamada implementation preserved at git tag/commit baseline `yamada_end`.

## [1.0.0] — 2026-08-10

### Added
- Quanta Streamlit app: Gaussian 09 job queue, SQLite persistence, EN/RU UI.
- RDKit import for mol2 / pdb / sdf; OPT B3LYP/6-31G(d) `pop=full` job builder.
- Yamada & Sato (TANSO 2015) XPS pipeline: log parse, core levels, Voigt spectra.
- Portable archive export/import (Windows → Mac analysis-only workflow).
- Melanine fixture tests; five-layer `src/` architecture and project docs.
