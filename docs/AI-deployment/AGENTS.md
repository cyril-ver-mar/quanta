# AGENTS — using AI-deployment in a new project

You are an AI coding agent. If you find this folder at the **project root** as `AI-deployment/`, follow this workflow.

## 0. Detect

```text
<project_root>/AI-deployment/   ← kit just pasted
```

Do **not** leave the kit at the root forever. Relocate it so the working tree stays clean.

## 1. Relocate the kit (required)

1. Ask the user where to park it (default: `docs/AI-deployment/`).  
2. Move the whole tree there (preserve structure).  
3. Add a short pointer in the project `README.md`:

```markdown
## Agent / architecture kit
See [docs/AI-deployment/](docs/AI-deployment/) — deploy checklist and Streamlit playbooks.
```

4. Prefer **not** committing secrets or generated `venv/`; the kit itself is documentation — commit when the user asks.

## 2. Read before scaffolding

In order:

1. `DEPLOY_CHECKLIST.md` — **ask the user** every section (implement: yes / no / later)  
2. `ARCHITECTURE.md` — default layering, run pattern, **general AI checklist**  
3. `SKILLS_GUIDE.md` — which skills to invoke  
4. Relevant `TASK_PLAYBOOKS/*.md` for “yes” items  
5. `TEMPLATES/` for file shapes (including `Instruction_Streamlit_TEMPLATE.md`)  
6. `EXAMPLES/chemistry/` only if the project is chemistry / cheminformatics  

Also run personal skill **`project-jumpstart`** and **`clarify-algorithm`** when available.

## 3. Deploy sequence

1. Confirm project root path (never use `$HOME` as git root).  
2. Run the **DEPLOY_CHECKLIST** Q&A; record answers in `docs/DECISIONS.md` (create if missing).  
3. Git init + `.gitignore` (adapt from `TEMPLATES/gitignore.example`).  
4. Python venv (prefer **3.11** unless user overrides).  
5. Install agreed Cursor rules from `CURSOR/rules/` into `.cursor/rules/` (only those the user accepted).  
6. Scaffold folders from `TEMPLATES/` + agreed playbooks.  
7. Create living instruction snapshot if the user wants it (`TEMPLATES/Instruction_Streamlit_TEMPLATE.md` → `docs/` or `Legacy/`).  

## 4. Rules vs playbooks

| Kind | Role |
|------|------|
| **Rules** (`.cursor/rules/*.mdc`) | Short always-on constraints |
| **Playbooks** | How to implement a concern — only if user said **yes** |
| **Examples/chemistry** | Particular patterns — copy/adapt, do not force on non-chem apps |

## 5. Do / don’t

**Do**

- Ask before adopting each playbook principle  
- Ask how secrets and local data should work for *this* project  
- Keep presentation thin; put logic in services / domain layers  
- One clear responsibility per module  

**Don’t**

- Assume chemistry, SQLite, or bilingual UI without confirmation  
- Commit `.streamlit/secrets.toml`, `venv/`, or bulk `data/` unless the user explicitly wants that layout and policy  
- Paste huge guides into rules — keep rules short, link to `docs/`  
- Start packaging / freeze builds unless the user asks  

## 6. After first scaffold

Remind the user (briefly): commit when ready, activate venv, fill secrets only in the agreed place.
