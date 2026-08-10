# Deploy checklist — ask the user first

When deploying this kit into a **new** project, walk through every section.  
For each item record: **yes** / **no** / **later**, plus any notes.  
Save the answers in `docs/DECISIONS.md` (or create it).

Default prompt style:

> “Do you want to implement **\<principle\>** in this project? (yes / no / later)”

---

## A. Project basics

| # | Question | Notes |
|---|----------|--------|
| A1 | Exact project root path? | Never `$HOME` as git root |
| A2 | App display name? | |
| A3 | Python version? | Kit default: **3.11** |
| A4 | Multi-page Streamlit? | vs single `app.py` |
| A5 | Git init + `.gitignore` now? | |

---

## B. Architecture & layering

| # | Principle (playbook) | Implement? |
|---|----------------------|------------|
| B1 | Five-layer `src/` (`utils` → `core` → `db` → `services` → `ui`) | |
| B2 | Living instruction doc (`Instruction_Streamlit_YYYY-MM-DD.md`) | |
| B3 | Code Complete / SRP habits (short rule) | |

→ See `ARCHITECTURE.md`, `TASK_PLAYBOOKS/02_five_layer_architecture.md`

---

## C. Streamlit UX & state

| # | Principle | Implement? |
|---|-----------|------------|
| C1 | Multi-page layout + navigation map | |
| C2 | `session_state` init in entrypoint; safe `.get()` | |
| C3 | Widget pending-key pattern (no assign after instantiate) | |
| C4 | Soft cancel for jobs expected > ~20s | |
| C5 | i18n helper (EN now, bilingual later) | |

→ `TASK_PLAYBOOKS/01_multipage_session_state.md`, `03_widget_pending_keys.md`, `04_long_jobs_soft_cancel.md`, `07_i18n.md`

---

## D. Data & persistence

| # | Principle | Implement? |
|---|-----------|------------|
| D1 | SQLite (or other DB) vs files-only | Ask engine |
| D2 | Backup before destructive writes | |
| D3 | Pagination for large tables | |

→ `TASK_PLAYBOOKS/05_sqlite_and_backups.md`

---

## E. Secrets & local data (**always ask — project-specific**)

Do **not** assume the Virtual Screening layout. Clarify:

| # | Question |
|---|----------|
| E1 | Where do API keys / secrets live? (e.g. `.streamlit/secrets.toml`, env vars, OS keychain) |
| E2 | What must be gitignored? (`venv/`, `data/`, `exports/`, vendor trees, …) |
| E3 | Is there a per-project data directory? Global admin store? |
| E4 | Logging destination? |

→ `TASK_PLAYBOOKS/06_secrets_and_local_data.md`

---

## F. Quality & process

| # | Principle | Implement? |
|---|-----------|------------|
| F1 | pytest (+ optional Streamlit AppTest) | |
| F2 | Polish pipeline (triage → phased commits) | |
| F3 | Capture decisions into `docs/DECISIONS.md` + rules | |
| F4 | Packaging / freeze builds deferred | |

→ `TASK_PLAYBOOKS/08_testing.md`, `09_polish_pipeline.md`, `10_packaging_deferred.md`

---

## G. Domain extras

| # | Principle | Implement? |
|---|-----------|------------|
| G1 | Chemistry / RDKit stack (`EXAMPLES/chemistry/`) | |
| G2 | Vendor structure editors (JSME / Ketcher / Marvin) | |
| G3 | Other domain pack: ___ | |

---

## H. Cursor wiring

| # | Action | Do? |
|---|--------|-----|
| H1 | Install general rules from `CURSOR/rules/` into `.cursor/rules/` | |
| H2 | Install chemistry example rules (only if G1 = yes) | |
| H3 | Point user at personal skills in `SKILLS_GUIDE.md` | |

---

## Record template (paste into DECISIONS.md)

```markdown
## Deploy from AI-deployment (YYYY-MM-DD)

| ID | Choice | Notes |
|----|--------|-------|
| A3 | 3.11 | |
| B1 | yes | |
| E1 | .streamlit/secrets.toml | |
| G1 | no | |
```
