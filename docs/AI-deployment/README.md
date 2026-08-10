# AI-deployment — Streamlit project jumpstart kit

Portable kit for **Cursor** sessions starting a **new Streamlit app from scratch**.

Copy this entire folder to the **root** of a new project. The agent should then **relocate** it (see `AGENTS.md`) and follow the deploy checklist.

## What’s inside

| Path | Purpose |
|------|---------|
| `AGENTS.md` | **Start here** — agent workflow after the kit lands in a new repo |
| `DEPLOY_CHECKLIST.md` | Ask the user which principles to implement |
| `ARCHITECTURE.md` | General 5-layer Streamlit architecture |
| `SKILLS_GUIDE.md` | How to use Cursor skills (personal vs project) |
| `CURSOR/rules/` | Rule templates (general always-on; chemistry as *examples*) |
| `TEMPLATES/` | Short file skeletons (not a full runnable app) |
| `TASK_PLAYBOOKS/` | How to handle common Streamlit tasks |
| `EXAMPLES/chemistry/` | Domain-specific patterns (optional) |

## Design choices (this kit)

- **General core** + optional **chemistry** examples  
- **Snippets / skeletons**, not a mini demo app  
- **Ask before implementing** each playbook principle on a new project  
- **Secrets / data layout**: clarify per project (see checklist)  
- General practices drawn from living Instruction snapshots (layers, run pattern, AI do/don’t) — **not** product-specific phase changelogs

## Manual use (human)

1. Copy `AI-deployment/` → `/path/to/new-project/AI-deployment/`  
2. Open that project in Cursor and tell the agent: *“Deploy from AI-deployment”*  
3. Answer the checklist questions  
4. Let the agent move the kit under `docs/AI-deployment/` (or agreed path) and scaffold

## Related personal skills (on your machine)

See `SKILLS_GUIDE.md`. Typical: `project-jumpstart`, `clarify-algorithm`, `polish-pipeline`, `capture-project-decisions`.
