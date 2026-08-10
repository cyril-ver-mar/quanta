# Playbook 01 — Multi-page layout & session_state

**Checklist ID:** C1, C2  
**Ask user:** implement yes / no / later?

## Goal

Predictable navigation and session keys that never “mysteriously” missing.

## Pattern

1. `app.py` (or home page) initializes **every** key used across pages.  
2. Pages read with `st.session_state.get("key", default)`.  
3. Multi-page files under `pages/` with numeric prefixes (`1_Projects.py`, …).  
4. Document the page map in `docs/DECISIONS.md`.

## Anti-patterns

- Assuming a key exists  
- Writing business logic only in `pages/` without services  
- Different key names for the same concept on two pages  

## Skeleton

See `TEMPLATES/app.py`, `TEMPLATES/pages/1_Home.py`.
