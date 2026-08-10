# Skills guide — Cursor

Skills are reusable workflows. Prefer **personal** skills for habits you reuse across projects; **project** skills only when the workflow is repo-specific.

## Where skills live

| Kind | Path |
|------|------|
| Personal | `~/.cursor/skills/<name>/SKILL.md` |
| Project | `<repo>/.cursor/skills/<name>/SKILL.md` |
| Built-in | `~/.cursor/skills-cursor/` — **do not** put custom skills here |

Each skill needs YAML frontmatter: `name`, `description` (triggers discovery).

## When the agent should read a skill

If the task matches a skill’s `description`, **read the skill file first** and follow it.

## Recommended personal skills (this machine)

| Skill | Use when |
|-------|----------|
| `project-jumpstart` | New repo: git, gitignore, venv, rules skeleton |
| `clarify-algorithm` | Before non-trivial features / pipelines |
| `capture-project-decisions` | User locks choices → `docs/DECISIONS.md` + rules |
| `code-complete-principles` | Module design, naming, error handling |
| `polish-pipeline` | Many small bugs → phased polish commits |
| `developer-hygiene-reminders` | After meaningful progress: commit/venv/secrets (don’t nag) |
| `improve-professional-english` | User writes EN with mistakes; commit/PR wording |
| `programming-coaching` | Teach *why* when introducing advanced patterns |
| `streamlit-chemistry-app` | Chem / RDKit Streamlit scaffold |
| `sqlite-chemistry-db` | SQLite libraries, FP blobs, backups |
| `vendor-third-party` | JSME / Ketcher / Marvin under `vendor/` |
| `update-streamlit-instruction` | Refresh dated Instruction snapshot |
| `review-skills-at-milestones` | Audit skills/rules after a phase |
| `role-qa` / `role-backend` / `role-frontend` / `role-chemist` | Specialist review lenses |
| `multi-role-orchestra` | Combine role reviews |

## Rules vs skills

| | Rules (`.cursor/rules/*.mdc`) | Skills |
|--|------------------------------|--------|
| Scope | Always-on or glob-scoped | On-demand workflows |
| Size | Keep short (~50 lines) | Can be longer checklists |
| Content | Constraints | Step-by-step procedures |

Install rule **templates** from `CURSOR/rules/` only after the user accepts them in `DEPLOY_CHECKLIST.md`.

## Deploy tip

On a new machine, copy needed personal skills into `~/.cursor/skills/` once. Do not vendor entire skill trees into every repo unless the team shares project skills.
