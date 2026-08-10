"""L4 — example service orchestration."""

from __future__ import annotations

from src.core.item import Item


class ItemService:
    """Use-cases live here; UI calls this, not SQL."""

    def create(self, name: str) -> Item:
        return Item(id="tmp", name=name.strip())
