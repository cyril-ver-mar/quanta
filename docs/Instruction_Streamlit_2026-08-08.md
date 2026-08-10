# Instruction_Streamlit_2026-08-08 — Quanta

## Purpose

Manage Gaussian 09 DFT (OPT B3LYP/6-31G(d) `pop=full`) for XPS-oriented analysis of C/N/O, with SQLite job tracking and portable archives for Mac-side analysis.

## How to run

```bash
./install.sh && ./run.sh
```

Windows: `install.bat` / `run.bat`.

## Folder tree

See `docs/ARCHITECTURE.md`.

## Five layers

`pages/ui → services → db → core → utils`

## Decisions

`docs/DECISIONS.md`

## AI do / don’t

**Do:** keep Gaussian I/O and XPS math out of Streamlit pages; soft-cancel long runs; backup DB before deleting jobs.  
**Don’t:** commit `data/`, `venv/`, secrets; assume ORCA in v1; run Gaussian on Mac without an executable path.
