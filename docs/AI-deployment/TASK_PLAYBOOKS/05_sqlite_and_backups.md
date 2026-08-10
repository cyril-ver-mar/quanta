# Playbook 05 — SQLite & backups

**Checklist ID:** D1–D3  
**Ask user:** implement yes / no / later? Also ask: SQLite vs other store.

## Goal

Safe persistence for thousands–hundreds of thousands of rows.

## Defaults (if user says yes)

- One DB file per project (or one global + per-project — **ask**).  
- Repositories hide SQL.  
- **Backup before** destructive / mass mutations (one backup per batch).  
- Prefer transactional commits for related writes.  
- Paginate UI reads; don’t load whole tables into memory.

## Chemistry note

If using compound libraries: store descriptors + fingerprints on write; see `EXAMPLES/chemistry/`.
