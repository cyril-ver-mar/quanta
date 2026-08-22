"""L1 — soft / hard cancel flags for long jobs."""

from __future__ import annotations

from src.utils.paths import CANCEL_FLAG, HARD_STOP_FLAG, ensure_runtime_dirs


def request_soft_cancel() -> None:
    ensure_runtime_dirs()
    CANCEL_FLAG.write_text("1", encoding="utf-8")


def request_hard_stop() -> None:
    ensure_runtime_dirs()
    HARD_STOP_FLAG.write_text("1", encoding="utf-8")
    CANCEL_FLAG.write_text("1", encoding="utf-8")


def clear_cancel_flags() -> None:
    for flag in (CANCEL_FLAG, HARD_STOP_FLAG):
        if flag.exists():
            flag.unlink()


def soft_cancel_requested() -> bool:
    return CANCEL_FLAG.exists()


def hard_stop_requested() -> bool:
    return HARD_STOP_FLAG.exists()
