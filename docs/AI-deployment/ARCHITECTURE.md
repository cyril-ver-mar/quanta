# Architecture — Streamlit apps (general)

Extracted from living Instruction snapshots (universal patterns only).  
Specialize after `DEPLOY_CHECKLIST.md`. Domain-specific details stay in `EXAMPLES/` or `docs/DECISIONS.md`.

**Conflict rule:** If a notebook / ad-hoc script and this guide disagree → **follow this architecture** (and the project’s dated Instruction once it exists).

---

## 1. How to run (typical)

Prefer scripts-first (ask user for exact names):

```bash
./install.sh    # once — Python venv + deps (prefer 3.11 unless user overrides)
./run.sh        # starts Streamlit (often via launch.py) → http://localhost:8501
```

Windows often: `install.bat` / `run.bat`.  
Secrets: commit an **example** file only; never real secrets (clarify location in checklist E*).

Optional sidebar patterns (if user accepts playbooks): soft cancel; Exit that stops the server cleanly.

Tests (if F1 = yes):

```bash
./venv/bin/python -m pytest tests/ -q -m "not slow"
```

---

## 2. Folder map (default)

```text
app.py                 # entry: set_page_config, session_state init, navigation only
launch.py              # optional process wrapper
install.sh | run.sh    # (+ .bat on Windows)
pages/                 # Streamlit multi-page (numeric prefixes)
src/
  utils/               # L1 infrastructure: paths, logging, cancel, config
  core/                # L2 domain models / pure logic (no Streamlit, no DB I/O)
  db/                  # L3 data access: connections, schema, repositories
  services/            # L4 orchestration: use-cases, import/export, engines
  ui/                  # L5 presentation: components (thin)
docs/                  # DECISIONS, ARCHITECTURE, relocated AI-deployment
tests/
fixtures/              # optional sample data for demos/tests
.cursor/rules/         # short always-on conventions
data/                  # runtime (usually gitignored) — ask user
exports/               # optional output dir — ask user
```

Exact tree belongs in the project’s dated Instruction after scaffold.

---

## 3. Five layers (import direction)

```text
ui / pages  →  services  →  db  →  core  →  utils
```

| Layer | Path | Responsibility |
|-------|------|----------------|
| 1 Infrastructure | `src/utils/` | paths, logging, cancel tokens/flags, small config helpers |
| 2 Domain | `src/core/` | pure models & algorithms — **no** Streamlit, **no** SQL |
| 3 Data | `src/db/` | connections, schema, repositories; backup before destructive ops |
| 4 Application | `src/services/` | use-cases, engines, import/export, side effects |
| 5 Presentation | `src/ui/`, `pages/`, `app.py` | Streamlit only — **no** domain algorithms |

Principles: information hiding, SRP (Code Complete) + short `.cursor/rules/`.

### Entry responsibilities

`app.py` / home should only:

1. `st.set_page_config`  
2. Initialize every `session_state` key used across pages  
3. Render shell / navigation  

Business work lives in `services` + thin `ui` components.

---

## 4. Product decisions

Keep the full table in `docs/DECISIONS.md` (create from `TEMPLATES/DECISIONS.template.md`).  
This kit does **not** invent product rules — ask via `DEPLOY_CHECKLIST.md`.

---

## 5. Optional domain packs

- **Chemistry / RDKit:** `EXAMPLES/chemistry/` (only if checklist G1 = yes)  
- Other domains: add under `EXAMPLES/<name>/` the same way  

---

## 6. AI assistant checklist (general)

**Do**

- [ ] Place code in the correct layer  
- [ ] Initialize `session_state` keys; read with `.get()`  
- [ ] Backup storage before destructive / mass writes (if DB enabled)  
- [ ] Soft-cancel work expected to take **> ~20 seconds** (if playbook C4 = yes)  
- [ ] Validate external inputs; log failures; never swallow exceptions  
- [ ] Update the dated Instruction when structure / public APIs change (if B2 = yes)  
- [ ] Ask before adopting each playbook principle  

**Don’t**

- [ ] Put domain algorithms or raw SQL in Streamlit pages/widgets  
- [ ] Commit `venv/`, secrets, or bulky runtime data unless the user agreed  
- [ ] Use an untested bleeding-edge Python for stacks that need a pin (e.g. chem → prefer 3.11)  
- [ ] Treat alternate UI frameworks as primary if the project chose Streamlit  
- [ ] Store generated preview images in the DB when “depict on review” was chosen  

Chemistry-specific do/don’t extras: `EXAMPLES/chemistry/README.md`.
