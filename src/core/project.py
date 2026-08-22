"""Quanta analysis project domain model (Layer 2).

A project groups compound entries (molecules) and their ΔSCF jobs — analogous to
XPS-Deconv projects grouping spectrum entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CompoundEntry:
    """One molecule registered in a project (links to ``compounds`` table)."""

    id: str = field(default_factory=lambda: uuid4().hex[:10])
    label: str = ""
    compound_id: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "compound_id": self.compound_id,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompoundEntry:
        return cls(
            id=str(data.get("id") or uuid4().hex[:10]),
            label=str(data.get("label", "")),
            compound_id=int(data.get("compound_id") or 0),
            notes=str(data.get("notes", "")),
        )


@dataclass
class QuantaProject:
    id: str = field(default_factory=lambda: uuid4().hex[:10])
    name: str = "Untitled project"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    notes: str = ""
    entries: list[CompoundEntry] = field(default_factory=list)
    active_entry_id: str | None = None

    def touch(self) -> None:
        self.updated_at = _now()

    def get_active(self) -> CompoundEntry | None:
        if not self.active_entry_id:
            return None
        for entry in self.entries:
            if entry.id == self.active_entry_id:
                return entry
        return None

    def compound_ids(self) -> list[int]:
        return [e.compound_id for e in self.entries if e.compound_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "notes": self.notes,
            "entries": [e.to_dict() for e in self.entries],
            "active_entry_id": self.active_entry_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuantaProject:
        return cls(
            id=str(data.get("id") or uuid4().hex[:10]),
            name=str(data.get("name", "Untitled project")),
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
            notes=str(data.get("notes", "")),
            entries=[CompoundEntry.from_dict(e) for e in data.get("entries") or []],
            active_entry_id=data.get("active_entry_id"),
        )
