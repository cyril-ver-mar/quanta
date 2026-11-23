"""L4 — import structures with RDKit and register compounds."""

from __future__ import annotations

import shutil
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from src.core.gaussian_input import DEFAULT_ROUTE, GaussianJobSpec, write_gjf
from src.core.models import Compound
from src.db.repositories import CompoundRepository
from src.utils.logging_setup import get_logger
from src.utils.paths import DATA_DIR, ensure_runtime_dirs

logger = get_logger("quanta.compounds")

SUPPORTED = {".mol2", ".pdb", ".sdf", ".mol"}
PERIODIC_SUFFIXES = {".cif", ".poscar", ".vasp", ".xyz", ".extxyz", ".traj"}
PERIODIC_NAMES = {"poscar", "contcar", "poscar.vasp"}


def _load_mol(path: Path) -> Chem.Mol:
    suffix = path.suffix.lower()
    if suffix == ".mol2":
        mol = Chem.MolFromMol2File(str(path), removeHs=False)
    elif suffix == ".pdb":
        mol = Chem.MolFromPDBFile(str(path), removeHs=False)
    elif suffix in {".sdf", ".mol"}:
        suppl = Chem.SDMolSupplier(str(path), removeHs=False)
        mol = next((m for m in suppl if m is not None), None)
    else:
        raise ValueError(f"Unsupported format: {suffix}")
    if mol is None:
        raise ValueError(f"RDKit failed to read {path}")
    if mol.GetNumConformers() == 0:
        raise ValueError(f"No 3D conformer in {path}; provide 3D coordinates")
    return mol


def mol_to_atoms(mol: Chem.Mol) -> list[tuple[str, float, float, float]]:
    conf = mol.GetConformer()
    atoms: list[tuple[str, float, float, float]] = []
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        atoms.append((atom.GetSymbol(), float(pos.x), float(pos.y), float(pos.z)))
    return atoms


def element_counts(mol: Chem.Mol) -> dict[str, int]:
    counts: dict[str, int] = {}
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        counts[sym] = counts.get(sym, 0) + 1
    return counts


class CompoundService:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.repo = CompoundRepository()
        self.store = DATA_DIR / "compounds"
        self.store.mkdir(parents=True, exist_ok=True)

    def import_file(
        self,
        uploaded_path: Path,
        name: str | None = None,
        charge: int = 0,
        multiplicity: int = 1,
        *,
        source_name: str | None = None,
    ) -> int:
        path = Path(uploaded_path)
        label = source_name or path.name
        if _is_periodic_name(label) or path.suffix.lower() in PERIODIC_SUFFIXES:
            return self._import_periodic(
                path,
                name=name,
                charge=charge,
                multiplicity=multiplicity,
                source_name=label,
            )
        if path.suffix.lower() not in SUPPORTED and Path(label).suffix.lower() not in SUPPORTED:
            raise ValueError(
                "Supported molecules: mol2, pdb, sdf, mol. "
                "Supported periodic structures: cif, poscar, vasp, extxyz."
            )
        mol = _load_mol(path)
        dest = self.store / path.name
        shutil.copy2(path, dest)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        compound = Compound(
            id=None,
            name=name or path.stem,
            source_format=path.suffix.lower().lstrip("."),
            source_path=str(dest),
            charge=charge,
            multiplicity=multiplicity,
            formula=formula,
            n_atoms=mol.GetNumAtoms(),
            meta_json={
                "mw": float(Descriptors.MolWt(mol)),
                "elements": element_counts(mol),
            },
        )
        cid = self.repo.add(compound)
        logger.info("Imported compound %s id=%s", compound.name, cid)
        return cid

    def list_compounds(self) -> list[Compound]:
        return self.repo.list_all()

    def list_compounds_for_project(self, compound_ids: list[int]) -> list[Compound]:
        if not compound_ids:
            return []
        id_set = set(compound_ids)
        return [c for c in self.repo.list_all() if c.id in id_set]

    def get(self, compound_id: int) -> Compound | None:
        return self.repo.get(compound_id)

    def update_charge_mult(self, compound_id: int, charge: int, multiplicity: int) -> None:
        self.repo.update_charge_mult(compound_id, charge, multiplicity)

    def load_molecule(self, compound: Compound) -> Chem.Mol:
        return _load_mol(Path(compound.source_path))

    def build_gjf_text(
        self,
        compound: Compound,
        nproc: int,
        mem_mb: int,
        route: str = DEFAULT_ROUTE,
        chk_name: str = "job.chk",
    ) -> str:
        mol = _load_mol(Path(compound.source_path))
        atoms = mol_to_atoms(mol)
        spec = GaussianJobSpec(
            title=compound.name,
            charge=compound.charge,
            multiplicity=compound.multiplicity,
            atoms=atoms,
            chk_name=chk_name,
            nproc=nproc,
            mem_mb=mem_mb,
            route=route,
        )
        return write_gjf(spec)

    def _import_periodic(
        self,
        path: Path,
        *,
        name: str | None,
        charge: int,
        multiplicity: int,
        source_name: str,
    ) -> int:
        from src.core.periodic import (
            element_counts as count_elements,
            formula_from_symbols,
            read_periodic_structure,
        )

        structure = read_periodic_structure(str(path), source_name=source_name)
        suffix = Path(source_name).suffix.lower().lstrip(".") or "extxyz"
        dest_name = source_name if Path(source_name).suffix else f"{Path(source_name).name}.extxyz"
        dest = self.store / dest_name
        if path.resolve() != dest.resolve():
            shutil.copy2(path, dest)
        counts = count_elements(structure.symbols)
        compound = Compound(
            id=None,
            name=name or Path(source_name).stem,
            source_format=suffix,
            source_path=str(dest),
            charge=charge,
            multiplicity=multiplicity,
            formula=formula_from_symbols(structure.symbols),
            n_atoms=structure.n_atoms,
            meta_json={
                "periodic": True,
                "elements": counts,
                "symbols": list(structure.symbols),
                "positions": [list(p) for p in structure.positions],
                "cell": [list(row) for row in structure.cell],
                "pbc": list(structure.pbc),
            },
        )
        cid = self.repo.add(compound)
        logger.info("Imported periodic structure %s id=%s", compound.name, cid)
        return cid


def _is_periodic_name(name: str) -> bool:
    stem = Path(name).name.lower()
    if stem in PERIODIC_NAMES:
        return True
    return Path(name).suffix.lower() in PERIODIC_SUFFIXES
