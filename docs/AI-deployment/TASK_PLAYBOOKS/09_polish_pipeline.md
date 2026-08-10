# Playbook 09 — Polish pipeline

**Checklist ID:** F2  
**Ask user:** implement yes / no / later?

## Goal

Turn a dump of small bugs into phased work: triage → one phase per session → tests → commit (if asked).

## Severity

| Tier | Meaning |
|------|---------|
| P0 | Crash / wrong data / broken primary path |
| P1 | Half-broken trust / labels / metadata |
| P2 | Hard to use / see |
| P3 | Nice-to-have |

## Habit

Use personal skill `polish-pipeline` when available. Don’t mix P0 crashes with P3 cosmetics in one commit unless the user insists.
