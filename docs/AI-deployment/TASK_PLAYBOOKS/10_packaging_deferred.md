# Playbook 10 — Packaging deferred

**Checklist ID:** F4  
**Ask user:** implement yes / no / later?

## Goal

Ship a **scripts-first** app (`install` / `run` + optional `launch.py`) before PyInstaller / Briefcase / freeze.

## Do

- Document `./run.sh` (or OS equivalents) as the supported path.  
- Keep optional vendor binaries / cloud keys degrading gracefully.  

## Don’t

- Block feature work on packaging.  
- Assume vendor editor assets exist in every clone.
