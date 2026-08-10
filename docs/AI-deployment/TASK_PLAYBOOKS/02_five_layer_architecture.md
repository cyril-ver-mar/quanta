# Playbook 02 — Five-layer architecture

**Checklist ID:** B1  
**Ask user:** implement yes / no / later?

## Goal

Thin UI; testable domain; swappable storage/editors.

## Layers

`ui → services → db → core → utils` (imports only downward).

| Layer | Contains | Must not |
|-------|----------|----------|
| utils | paths, logging, cancel | business rules |
| core | domain types, pure algorithms | Streamlit, SQL |
| db | repositories, schema | widgets |
| services | use-cases, orchestration | raw `st.*` |
| ui | components, pages | chemistry/SQL algorithms |

## When to skip

Tiny script apps may use fewer layers — only if the user chooses **no** / **later**.
