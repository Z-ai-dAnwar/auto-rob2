from pathlib import Path

import pytest

from rob2_pipeline.io import discover_pdf_inputs, discover_supplements_for_pdf


def test_discover_pdf_inputs_single_file(tmp_path):
    pdf = tmp_path / "trial.pdf"
    pdf.write_bytes(b"%PDF-1.7")

    assert discover_pdf_inputs(str(pdf)) == [pdf]


def test_discover_pdf_inputs_directory_sorted(tmp_path):
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    assert discover_pdf_inputs(str(tmp_path)) == [
        tmp_path / "a.pdf",
        tmp_path / "b.pdf",
    ]


def test_discover_pdf_inputs_rejects_non_pdf_file(tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="not a PDF"):
        discover_pdf_inputs(str(txt))


def test_discover_pdf_inputs_empty_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="No PDF files"):
        discover_pdf_inputs(str(tmp_path))


def test_discover_pdf_inputs_missing_path():
    with pytest.raises(FileNotFoundError, match="does not exist"):
        discover_pdf_inputs(str(Path("missing.pdf")))


def test_discover_supplements_for_pdf_uses_pdf_stem(tmp_path):
    supplement_root = tmp_path / "supplements"
    trial_dir = supplement_root / "TITAN"
    trial_dir.mkdir(parents=True)
    protocol = trial_dir / "protocol.pdf"
    appendix = trial_dir / "appendix.pdf"
    protocol.write_bytes(b"pdf")
    appendix.write_bytes(b"pdf")

    result = discover_supplements_for_pdf(tmp_path / "TITAN.pdf", supplement_root)

    assert result == [appendix, protocol]


def test_discover_supplements_for_pdf_returns_empty_without_matching_folder(tmp_path):
    assert discover_supplements_for_pdf(tmp_path / "TITAN.pdf", tmp_path) == []


def test_main_rejects_explicit_supplement_for_directory_input(tmp_path, monkeypatch):
    import sys

    import main as cli

    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.7")
    supplement = tmp_path / "protocol.pdf"
    supplement.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", str(tmp_path), "--supplement", str(supplement)],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 2
