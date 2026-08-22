"""Gaussian log diagnostic extraction."""

from __future__ import annotations

from pathlib import Path

from src.services.gaussian_parser import extract_error_snippets, parse_gaussian_log, tail_lines


def test_extract_error_snippets_keeps_context(tmp_path: Path) -> None:
    log = tmp_path / "fail.log"
    log.write_text(
        "\n".join(
            [
                "line before",
                "more context",
                " Error termination via Lnk1e at Sat.",
                " Error: segmentation violation",
                "after",
            ]
        ),
        encoding="utf-8",
    )
    parsed = parse_gaussian_log(log)
    assert parsed.raw_errors
    assert "Error termination" in parsed.raw_errors[0]
    assert "segmentation" in parsed.raw_errors[0]


def test_tail_lines() -> None:
    text = "\n".join(str(i) for i in range(200))
    out = tail_lines(text, 10)
    assert out.splitlines()[0] == "190"
    assert out.splitlines()[-1] == "199"


def test_extract_empty() -> None:
    assert extract_error_snippets("Normal termination of Gaussian 09") == []


def test_scf_done_parses_hyphenated_method(tmp_path: Path) -> None:
    """PBE labels are E(RPBE-PBE) / E(UPBE-PBE) — hyphen must not break the regex."""
    from src.services.gaussian_parser import final_scf_energy_ha, parse_gaussian_log

    log = tmp_path / "neutral.log"
    log.write_text(
        " SCF Done:  E(RPBE-PBE) =  -79.6987024059     A.U. after    3 cycles\n"
        "Normal termination of Gaussian 09 at Sun Aug 23 01:37:08 2026.\n",
        encoding="utf-8",
    )
    parsed = parse_gaussian_log(log)
    assert parsed.method == "RPBE-PBE"
    assert final_scf_energy_ha(parsed) == -79.6987024059
