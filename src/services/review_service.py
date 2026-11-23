"""L4 — compound review context (structure + related jobs)."""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem

from src.core.models import Compound, Job
from src.core.structure_export import atom_table, mol_to_block
from src.db.repositories import JobRepository
from src.services.compound_service import CompoundService


@dataclass
class ReviewBundle:
    compound: Compound
    mol: Chem.Mol | None
    mol_block: str
    atoms: list[dict]
    jobs: list[Job]
    periodic: bool = False
    cell: list | None = None


class ReviewService:
    def __init__(self) -> None:
        self.compounds = CompoundService()
        self.jobs = JobRepository()

    def load(self, compound_id: int, view_format: str = "mol") -> ReviewBundle:
        compound = self.compounds.get(compound_id)
        if compound is None:
            raise ValueError(f"Compound {compound_id} not found")
        if (compound.meta_json or {}).get("periodic"):
            return self._load_periodic(compound)
        mol = self.compounds.load_molecule(compound)
        return ReviewBundle(
            compound=compound,
            mol=mol,
            mol_block=mol_to_block(mol, view_format),
            atoms=atom_table(mol),
            jobs=self.jobs.list_by_compound(compound_id),
        )

    def _load_periodic(self, compound: Compound) -> ReviewBundle:
        meta = compound.meta_json or {}
        symbols = list(meta.get("symbols") or [])
        positions = list(meta.get("positions") or [])
        atoms = []
        for i, (sym, pos) in enumerate(zip(symbols, positions, strict=False), start=1):
            atoms.append(
                {
                    "atom": i,
                    "element": sym,
                    "x": float(pos[0]),
                    "y": float(pos[1]),
                    "z": float(pos[2]),
                }
            )
        return ReviewBundle(
            compound=compound,
            mol=None,
            mol_block="",
            atoms=atoms,
            jobs=self.jobs.list_by_compound(int(compound.id or 0)),
            periodic=True,
            cell=meta.get("cell"),
        )
