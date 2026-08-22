#!/usr/bin/env python3
"""Generate Chong-2007 style test structures (ethane, hydrazine) as mol2.

Usage (from project root, venv active):
  python scripts/make_chong_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem, rdMolDescriptors

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "chong2007"

# Chong 2007, J. Electron Spectrosc. Relat. Phenom. 159, 94–96 — Table 1 (eV)
# Method in paper: E(PW86-PW91)+C_rel / TZP // exp. geometry — NOT identical to Quanta PBE/6-31G(d).
REFERENCE = {
    "citation": "Chong, D. P. J. Electron Spectrosc. Relat. Phenom. 159 (2007) 94–96",
    "note": (
        "Observed CEBEs from Jolly et al. (as cited by Chong). "
        "Quanta default PBE/6-31G(d) ΔSCF will not match absolute values exactly; "
        "use for workflow smoke-test (OPT→neutral→core-hole→BE table). "
        "Prefer raw BEs (C1s shift off) when comparing to gas-phase CEBE tables."
    ),
    "molecules": {
        "ethane": {
            "formula": "C2H6",
            "smiles": "CC",
            "elements": {"C": 2, "H": 6},
            "core_levels": "C1s",
            "n_corehole_jobs": 2,
            "chong_obs_ev": {"C1s": 290.72},
            "chong_loc_ev": {"C1s": 290.88},
        },
        "hydrazine": {
            "formula": "N2H4",
            "smiles": "NN",
            "elements": {"N": 2, "H": 4},
            "core_levels": "N1s",
            "n_corehole_jobs": 2,
            "chong_obs_ev": {"N1s": 406.1},
            "chong_loc_ev": {"N1s": 406.25},
        },
    },
}


def _embed(mol: Chem.Mol) -> Chem.Mol:
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 0xC407
    code = AllChem.EmbedMolecule(mol, params)
    if code != 0:
        raise RuntimeError("RDKit EmbedMolecule failed")
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    return mol


def _mol_to_mol2_block(mol: Chem.Mol, name: str) -> str:
    """Write a Tripos mol2 block (RDKit has no MolToMol2File in many builds)."""
    if mol.GetNumConformers() < 1:
        raise ValueError("molecule has no conformer for mol2")
    conf = mol.GetConformer()
    n_atoms = mol.GetNumAtoms()
    n_bonds = mol.GetNumBonds()

    atom_lines: list[str] = []
    for i, atom in enumerate(mol.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        sym = atom.GetSymbol()
        atom_name = f"{sym}{i + 1}"
        # Sybyl type: element is enough for these fixtures / RDKit MolFromMol2File
        sybyl = sym
        atom_lines.append(
            f"{i + 1:>7d} {atom_name:<8s} {pos.x:9.4f} {pos.y:9.4f} {pos.z:9.4f} "
            f"{sybyl:<6s} 1 <1>           0.0000"
        )

    bond_order_map = {1: "1", 2: "2", 3: "3", 1.5: "ar"}
    bond_lines: list[str] = []
    for bi, bond in enumerate(mol.GetBonds()):
        order = bond.GetBondTypeAsDouble()
        bo = bond_order_map.get(order, "1")
        if bond.GetIsAromatic():
            bo = "ar"
        a1 = bond.GetBeginAtomIdx() + 1
        a2 = bond.GetEndAtomIdx() + 1
        bond_lines.append(f"{bi + 1:>6d} {a1:>4d} {a2:>4d} {bo}")

    parts = [
        "@<TRIPOS>MOLECULE",
        name,
        f" {n_atoms} {n_bonds} 0 0 0",
        "SMALL",
        "NO_CHARGES",
        "",
        "",
        "@<TRIPOS>ATOM",
        *atom_lines,
        "@<TRIPOS>BOND",
        *bond_lines,
        "",
    ]
    return "\n".join(parts)


def write_mol2(mol: Chem.Mol, path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_mol_to_mol2_block(mol, name), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reference.json").write_text(json.dumps(REFERENCE, indent=2) + "\n", encoding="utf-8")

    for key, meta in REFERENCE["molecules"].items():
        mol = Chem.MolFromSmiles(meta["smiles"])
        if mol is None:
            raise SystemExit(f"Bad SMILES for {key}")
        mol = _embed(mol)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        out = OUT / f"{key}.mol2"
        write_mol2(mol, out, key)
        print(f"Wrote {out} ({formula}, {mol.GetNumAtoms()} atoms)")

    print(f"Reference: {OUT / 'reference.json'}")


if __name__ == "__main__":
    main()
