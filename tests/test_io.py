from pathlib import Path

import pytest

from rob2_pipeline.io import discover_pdf_inputs


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
