# Changelog

All notable changes to this project are listed here.  
Version source of truth: root `VERSION`. Git tags: `vMAJOR.MINOR.PATCH`.

## [Unreleased]

## [1.0.23] — 2026-08-23

### Fixed
- **Core-hole 1s (not valence)** — Guess=Alter swaps the target 1s with the β vacancy MO (`n_occ` / former HOMO), not two occupied MOs; eigenvalue parser includes Gaussian continuation lines so `n_occ` is not under-counted.
- **Excel export** — soft-fail with install hint when `openpyxl` is missing; install smoke-tests include `openpyxl` / `scipy` / `PIL`.

### Changed
- **Lean GitHub source** — stop tracking `standalone/`, `standalone_version/`, `docs/AI-deployment/`, and `.cursor/`. Build end-user zips with `scripts/build_standalone.py` and attach them to Releases.

## [1.0.22] — 2026-08-23

### Added
- **Simulated XPS spectra on Results** — Gaussian / Lorentzian / Voigt / Pseudo-Voigt with global FWHM and GL fraction; toggleable reference BE overlays (Chong 2007 for ethane/hydrazine; XPS-Deconv library otherwise).
- **Spectrum exports** — CSV, Excel, PNG, JPEG, TIFF.
- **Translated Streamlit navigation** — sidebar page titles follow EN/RU language (same pattern as XPS-Deconv).

### Changed
- Chong / melanine **test molecules** moved from Results to **Compounds**.

## [1.0.21] — 2026-08-23

### Fixed
- **Could not read E₀** — parse `SCF Done: E(RPBE-PBE)` / `E(UPBE-PBE)` (hyphenated method labels); previous `\w+` regex skipped those lines.

## [1.0.20] — 2026-08-23

### Fixed
- **Core-hole SCF convergence** — add `SCF=(XQC,MaxCyc=512)` (still one `#` line, 69 chars) so DIIS stalls switch to quadratic convergence instead of failing at 128 cycles.

## [1.0.19] — 2026-08-23

### Fixed
- **Core-hole electron count** — ΔSCF CEBE uses the core-ionized cation (`charge = Q+1`); closed-shell neutrals get multiplicity 2 (e.g. ethane `1 2`, not `0 2`). Avoids G09 “multiplicity 2 and N electrons is impossible”.

## [1.0.18] — 2026-08-23

### Fixed
- **Core-hole QPErr root cause** — stop wrapping long `#` routes (G09 splits mid-token); use `UPBEPBE` instead of `uks PBEPBE`; enforce a single `#` line under ~70 characters.
- **Guess=Alter input** — replace invalid `Alter` / `swap` / `end` with G09 α/β blank-line sections (empty α, core↔HOMO on β).

## [1.0.17] — 2026-08-23

### Fixed
- **Core-hole QPErr on Windows G09W** — write `.gjf` with CRLF so multi-line `#` routes are not glued (`…checkpoint #`); shorten core-hole route (omit `Integral=` there) so it fits on one line.

## [1.0.9] — 2026-08-22

### Added
- **Chong 2007 smoke-test molecules** — `fixtures/chong2007/` ethane (C₂H₆) + hydrazine (N₂H₄) with Table 1 reference CEBEs; Results button to import into the active project.

### Fixed
- **Update check showed 1.0.0 as latest** — resolve newest semver from Releases *and* git tags (tags without a GitHub Release no longer hide newer versions).
- **SECRETS parsing** — keys are case-insensitive; clearer `SECRETS.example` (keep full `ghp_` / `github_pat_` token).

## [1.0.8] — 2026-08-22

### Fixed
- **GitHub update rate limit** — disk cache (1 h), 15 min backoff on 403, Settings no longer hits API every visit; optional token via root `SECRETS` file or env.

### Added
- **Root `SECRETS` file** — optional `KEY=value` secrets next to `app.py` (`SECRETS.example` template); app loads if present; preserved on in-app update; never committed / never shipped in standalone zip.
- **Settings → Secrets** — shows whether `SECRETS` exists and if a GitHub token is configured (never displays the token).

## [1.0.7] — 2026-08-22

### Added
- **Project page** (XPS-Deconv style): create/load/delete projects; compound entries in JSON + SQLite index; all workflow pages scoped to active project.

### Fixed
- **Workflow run failure** — `create_job` now saves ΔSCF step list to the database (steps were dropped on reload before update).

## [1.0.6] — 2026-08-22

### Fixed
- **GitHub update check** — parse `GITHUB_REPO` skipping `#` comment lines; handle UTF-8 BOM; ship one-line `GITHUB_REPO` in standalone.
- **Settings → Updates** — always re-reads config (no stale session cache after editing `GITHUB_REPO`); shows file path when misconfigured.

### Added
- Root **`GITHUB_REPO`** committed (`cyril-ver-mar/quanta`) so dev installs resolve updates out of the box.

## [1.0.5] — 2026-08-22

### Added
- **In-app updates** (XPS-Deconv style): GitHub Releases check on launch, sidebar banner, Settings → Updates, one-click install from standalone zip (preserves `data/`, `exports/`, `venv/`).

### Changed
- **run.bat** — Claude-style terminal UI (terracotta banner, colored status, boxed errors, version line, pause on failure).

## [1.0.4] — 2026-08-22

### Fixed
- **Windows double-click install** — single-window `.bat` (no `cmd /k` spawn); `cd /d "%~dp0"` first; visible `pause` at end.
- Bootstrap `.ps1` — TLS 1.2 for GitHub; errors show “Press Enter to close”; requires `.ps1` beside `.bat`.
- Added `install_quanta.cmd` duplicate launcher for Explorer.

## [1.0.3] — 2026-08-22

### Added
- **standalone_version/** bootstrap installers (XPS-style): `install_quanta.sh`, `install_quanta.bat`, `install_quanta.ps1` — download latest GitHub release zip.
- Full **standalone/Quanta/** distributable tree (app + pages + src + run scripts).
- `scripts/build_standalone.py` to rebuild the standalone folder.

### Changed
- **install.sh** / **install.bat** — clean 6-step install (Python 3.11, venv, pip, inline import check); no separate install Python scripts.
- **run.sh** / **run.bat** — verify deps before launch.
- **Windows bootstrap** — fallback to tag source zip when no release asset; `pause` on `.bat` so errors stay visible; prefer local `install_quanta.ps1`.

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
