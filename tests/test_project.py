"""Tests for Quanta project persistence (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.project import QuantaProject
from src.services import project_service


def test_create_load_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_service, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(project_service, "PROJECT_DB_PATH", tmp_path / "projects_index.db")

    proj = project_service.create_project("Test ΔSCF", notes="demo")
    project_service.add_compound_to_project(proj, 42, label="benzene")
    loaded = project_service.load_project(proj.id)

    assert loaded.name == "Test ΔSCF"
    assert len(loaded.entries) == 1
    assert loaded.entries[0].compound_id == 42
    assert loaded.active_entry_id == loaded.entries[0].id


def test_list_projects_sorted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_service, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(project_service, "PROJECT_DB_PATH", tmp_path / "projects_index.db")

    project_service.create_project("A")
    project_service.create_project("B")
    rows = project_service.list_projects()
    assert len(rows) == 2
    assert {r["name"] for r in rows} == {"A", "B"}


def test_project_serialization() -> None:
    proj = QuantaProject(name="X", notes="n")
    raw = proj.to_dict()
    back = QuantaProject.from_dict(raw)
    assert back.name == "X"
    assert back.notes == "n"
