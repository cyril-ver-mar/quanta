# Playbook 06 — Secrets & local data

**Checklist ID:** E1–E4  
**Always ask** — do not copy another project’s layout blindly.

## Questions for the user

1. Where should secrets live?  
2. What directories must never be committed?  
3. Where does runtime data / exports / logs go?  
4. Single-user local app vs shared deployment?

## Common Streamlit option (example only)

- Secrets: `.streamlit/secrets.toml` (gitignored) + `secrets.toml.example` committed  
- Ignore: `venv/`, `data/`, `exports/`, `*.db`, vendor blobs  

Adapt `.gitignore` from `TEMPLATES/gitignore.example` after answers.

## Logging

Failures must leave a trail (file or structured logs). No silent `except:`.
