"""L2 — domain models (no Streamlit / DB)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Compound:
    id: int | None
    name: str
    source_format: str
    source_path: str
    charge: int = 0
    multiplicity: int = 1
    formula: str = ""
    n_atoms: int = 0
    meta_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class Job:
    id: int | None
    compound_id: int
    name: str
    status: JobStatus
    route: str
    nproc: int
    mem_mb: int
    work_path: str = ""
    error: str = ""
    progress: float = 0.0
    meta_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class Orbital:
    index: int
    energy_ha: float
    occupancy: float
    symmetry: str = ""

    @property
    def energy_ev(self) -> float:
        return self.energy_ha * 27.211386245988


@dataclass
class CoreLevel:
    element: str
    atom_index: int | None
    orbital_index: int
    energy_ha: float
    binding_ev_raw: float
    binding_ev_scaled: float
    binding_ev_shifted: float
    binding_ev_final: float
