# Playbook 04 — Long jobs & soft cancel

**Checklist ID:** C4  
**Ask user:** implement yes / no / later?

## Goal

Jobs expected to take **> ~20 seconds** can be stopped without killing the OS process blindly.

## Pattern

1. `CancelToken` / flag file checked inside loops.  
2. Sidebar or header: “Request soft cancel”.  
3. Progress + ETA when useful (> ~5s).  
4. `try/finally` clears cancel state.

## UI

Show a clear message when cancel is honored at the next checkpoint.
