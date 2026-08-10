# App name — Instruction (TEMPLATE)

Living architecture guide for agents.  
Specialize after deploy checklist. Date the real file: `Instruction_Streamlit_YYYY-MM-DD.md`.

**Draft / kit:** `docs/AI-deployment/` (relocated kit)  
**Product decisions:** `docs/DECISIONS.md`  
**Conflict rule:** Instruction + architecture kit win over notebooks when patterns conflict.

---

## 1. Purpose

**UI name:** ___  
**Domain:** ___  
**Auth:** ___ (e.g. single-user, no login)  
**Language:** ___ (e.g. English now; bilingual later)

---

## 2. How to run

```bash
./install.sh    # once — venv + deps
./run.sh        # Streamlit (document URL/port)
```

Windows: `install.bat` / `run.bat` if used.  
Secrets: document example path only — never commit real secrets.

Tests (if enabled):

```bash
./venv/bin/python -m pytest tests/ -q -m "not slow"
```

---

## 3. Current tree

```
# Paste real tree after scaffold (app.py, pages/, src/*, docs/, tests/, …)
```

---

## 4. Five layers (import direction)

```
ui / pages  →  services  →  db  →  core  →  utils
```

| Layer | Path | Responsibility |
|-------|------|----------------|
| 1 Infrastructure | `src/utils/` | paths, logs, cancel, config |
| 2 Domain | `src/core/` | pure models/algorithms — no Streamlit, no DB |
| 3 Data | `src/db/` | SQLite/repos (or agreed store); backups |
| 4 Application | `src/services/` | orchestration / engines / I/O |
| 5 Presentation | `src/ui/`, `pages/` | Streamlit only |

See kit `ARCHITECTURE.md` for detail.

---

## 5. Product decisions (summary)

Full table: `docs/DECISIONS.md`. List only locked bullets here.

---

## 6. Domain invariants

List only what the user accepted (e.g. from `EXAMPLES/chemistry/` if chem).

---

## 7. UI map

| Area | Behavior |
|------|----------|
| Home | |
| … | |

---

## 8. Deferred / optional stubs

Things not enabled by default (vendor editors, cloud APIs, freeze builds, …).

---

## 9. AI assistant checklist

**Do**

- [ ] Place code in the correct layer  
- [ ] Initialize `session_state`; read with `.get()`  
- [ ] Backup before destructive writes (if applicable)  
- [ ] Soft-cancel long jobs if that playbook is on  
- [ ] Update this dated instruction when structure changes  

**Don’t**

- [ ] Put domain logic in Streamlit pages  
- [ ] Commit `venv/`, secrets, bulky runtime data without agreement  
- [ ] Ignore the deploy checklist “ask first” rule  

---

## 10. Changelog

- **YYYY-MM-DD:** initial scaffold from AI-deployment kit.
