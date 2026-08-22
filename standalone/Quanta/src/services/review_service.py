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
    mol: Chem.Mol
    mol_block: str
    atoms: list[dict]
    jobs: list[Job]


class ReviewService:
    def __init__(self) -> None:
        self.compounds = CompoundService()
        self.jobs = JobRepository()

    def load(self, compound_id: int, view_format: str = "mol") -> ReviewBundle:
        compound = self.compounds.get(compound_id)
        if compound is None:
            raise ValueError(f"Compound {compound_id} not found")
        mol = self.compounds.load_molecule(compound)
        return ReviewBundle(
            compound=compound,
            mol=mol,
            mol_block=mol_to_block(mol, view_format),
            atoms=atom_table(mol),
            jobs=self.jobs.list_by_compound(compound_id),
        )
