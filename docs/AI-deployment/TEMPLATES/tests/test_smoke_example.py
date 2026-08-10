"""Example unit test — replace with real domain tests."""

from __future__ import annotations

from src.core.item import Item


def test_item_requires_name() -> None:
    try:
        Item(id="1", name="  ")
        assert False, "expected ValueError"
    except ValueError:
        pass
