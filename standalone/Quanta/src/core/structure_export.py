"""L2 — export RDKit molecules to text blocks for viewers."""

from __future__ import annotations

from rdkit import Chem


def mol_to_block(mol: Chem.Mol, fmt: str = "mol") -> str:
    fmt = fmt.lower()
    if fmt in {"mol", "sdf"}:
        block = Chem.MolToMolBlock(mol)
        if not block:
            raise ValueError("RDKit could not write mol block")
        return block
    if fmt == "pdb":
        block = Chem.MolToPDBBlock(mol)
        if not block:
            raise ValueError("RDKit could not write PDB block")
        return block
    raise ValueError(f"Unsupported export format: {fmt}")


def atom_table(mol: Chem.Mol) -> list[dict[str, float | int | str]]:
    if mol.GetNumConformers() == 0:
        return []
    conf = mol.GetConformer()
    rows: list[dict[str, float | int | str]] = []
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        rows.append(
            {
                "index": atom.GetIdx() + 1,
                "element": atom.GetSymbol(),
                "x": round(float(pos.x), 4),
                "y": round(float(pos.y), 4),
                "z": round(float(pos.z), 4),
            }
        )
    return rows
