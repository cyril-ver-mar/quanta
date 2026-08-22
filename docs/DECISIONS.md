# Quanta — project decisions

**App display name:** Quanta  
**Version:** see root `VERSION` (semver). Git tags: `vMAJOR.MINOR.PATCH`.  
**Last updated:** 2026-08-23

## Locked

| Topic | Decision |
|-------|----------|
| Stack | Python 3.11 + Streamlit multipage + RDKit |
| Architecture | 5-layer `src/` (`utils` → `core` → `db` → `services` → `ui`) |
| Storage | SQLite for jobs/compounds; job files under `data/jobs/<id>/` |
| Secrets / paths | User-editable in Settings (Gaussian path, work/scratch dirs); optional `.streamlit/secrets.toml` later |
| UI language | EN / RU |
| Engine v1 | Gaussian 09 only (ORCA post-v1) |
| XPS method | Gas-phase **ΔSCF** in Gaussian 09: OPT → neutral SP (E₀) → UKS core-hole SP per C/N/O (`Guess=Alter`); BE = ΔE; optional C1s shift → 284.3 eV; Voigt FWHM ≈1.2 eV. Yamada (TANSO 2015) retired at tag `yamada_end`. |
| Inputs | mol2 / pdb / sdf via RDKit; charge & multiplicity editable |
| Resources default | `%mem=1500MB`, `%nprocshared=4`, one job at a time |
| Platforms | Windows: run + analyze; Mac: analyze + archive import only |
| PC health | Deferred |
| Structure editor | Not in v1 |
| Docs help page | Later (public sources when needed) |

## Deploy checklist answers

| ID | Principle | Answer |
|----|-----------|--------|
| A1 | Project root | `/Users/kirillverbilo/JP/PhD/!!!Quanta` |
| A2 | App name | Quanta |
| A3 | Python | 3.11 |
| A4 | Multipage Streamlit | yes |
| A5 | Git init in project | yes (not `$HOME`) |
| B1 | Five-layer src | yes |
| B2 | Living Instruction | yes |
| B3 | Code Complete rule | yes |
| C1–C4 | Pages, session_state, pending keys, soft cancel | yes |
| C5 | i18n EN/RU | yes |
| D1 | SQLite | yes |
| D2 | Backup before destructive | yes |
| E2 | gitignore data/, exports/, venv, secrets | yes |
| F1 | pytest smoke | later / light |
| F4 | Packaging deferred | yes |
| G1 | RDKit | yes |
| G2 | Structure editor | no (v1) |

## GitHub & versioning

| Topic | Decision |
|-------|----------|
| GitHub repo | `cyril-ver-mar/quanta` (public) |
| Version source | Root `VERSION` |
| Git tag | `v` + same number (annotated) |
| Changelog | `CHANGELOG.md` |
| Release ritual | Bump `VERSION` + `CHANGELOG` → commit `Release Quanta X.Y.Z` → tag → push → optional `gh release create` |

## Kit & lean GitHub source

Public repo `cyril-ver-mar/quanta` tracks **lean application source** only (app code, tests, docs, build scripts).

- **Cursor / agent kit** (if present locally under `.cursor/` or `docs/AI-deployment/`): stays on the developer machine; listed in `.gitignore`, not published on GitHub. Historical note: kit was once kept under `docs/AI-deployment/` in-repo; that layout is retired for the public tree.
- **End-user standalone** (`standalone/`, `standalone_version/`): built locally via `scripts/build_standalone.py`, gitignored; zip attached to GitHub **Releases**, not committed to the default branch.

*(2026-08-23)* Confirmed: stop tracking standalone builds and local bootstrap/kit paths; lean source on GitHub, distributables via Releases.
