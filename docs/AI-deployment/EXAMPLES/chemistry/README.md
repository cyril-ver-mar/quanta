# Chemistry examples (optional)

Use **only** when deploy checklist **G1 = yes**.

General patterns below are distilled from living Instruction § chemistry / AI notes.  
They are **examples**, not mandatory for non-chem apps.

## Suggested stack extras

| Topic | Hint |
|-------|------|
| Python | Prefer **3.11** for RDKit stability |
| Storage | SQLite per project (ask); optional global admin DB |
| Compounds | Canonical isomeric SMILES + InChIKey dedupe per library |
| On write | Store descriptors + **Morgan FP** blob; recompute when SMILES changes |
| 2D images | Depict on review (e.g. data URIs) — **never** store images in DB |
| Reactions | SMARTS; try relevant reactant orderings; dedupe; soft cancel if long |
| Editors | Local JSME; Ketcher/Marvin optional behind a shared editor protocol |
| Vendor | `vendor/` / `JSME/` usually gitignored — document how to obtain |
| Export | 3D SDF (Embed + MMFF/UFF) if the user wants it |

## Descriptor fields (example)

See `compound_fields.example.md`.

## Page map (example)

See `pages_map.example.md`.

## Chemistry AI extras (add to Instruction §9 if G1)

**Do**

- [ ] Persist agreed descriptors + Morgan FP on compound write  
- [ ] Generate 2D at view time only  
- [ ] Normalize tricky input (e.g. look-alike characters) before parse if needed  

**Don’t**

- [ ] Store depiction images in SQLite  
- [ ] Put RDKit reaction loops in Streamlit pages  

## Skills

`streamlit-chemistry-app`, `sqlite-chemistry-db`, `vendor-third-party`.
