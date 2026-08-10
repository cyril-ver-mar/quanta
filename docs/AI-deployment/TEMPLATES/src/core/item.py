"""L2 — example domain object (no Streamlit, no DB)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """Replace with your domain type."""

    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name required")
