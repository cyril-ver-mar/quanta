# Compound fields (example)

On create/import, consider storing (ask user which to keep):

- Canonical isomeric SMILES + InChIKey (dedupe key per library)
- Exact / average MW
- Formal charge; charge at pH 7 (document method — e.g. simple heuristic vs formal)
- HBD, HBA, LogP (e.g. Crippen), TPSA (e.g. Ertl), rotatable bonds, formula, ring count
- Morgan fingerprint blob — example defaults: radius **2**, nBits **2048**; prefer `MorganGenerator` when available

Recompute when SMILES changes.  
2D depiction: generate in UI (e.g. data URIs for tables) — **do not** persist images in DB.
