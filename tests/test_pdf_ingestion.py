import fitz

import rob2_pipeline.pdf_ingestion as pdf_ingestion
from rob2_pipeline.pdf_ingestion import cap_section, extract_full_text, parse_sections


def test_extract_full_text_from_synthetic_pdf_via_fallback(tmp_path, monkeypatch):
    pdf_path = tmp_path / "synthetic_trial.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Abstract\nThis was a randomized trial.\nMethods\nPatients were allocated.")
    doc.save(pdf_path)
    doc.close()

    monkeypatch.setattr(
        pdf_ingestion,
        "_extract_with_docling",
        lambda pdf_path: (_ for _ in ()).throw(RuntimeError("docling unavailable")),
    )

    text = extract_full_text(str(pdf_path))

    assert "Abstract" in text
    assert "randomized trial" in text


def test_extract_full_text_uses_docling_before_fallback(monkeypatch):
    calls = []

    def fake_docling(pdf_path):
        calls.append(("docling", pdf_path))
        return "Docling text\xa0with hyphen-\nbreaks"

    def fake_fallback(pdf_path):
        raise AssertionError("fallback should not be called")

    monkeypatch.setattr(pdf_ingestion, "_extract_with_docling", fake_docling)
    monkeypatch.setattr(pdf_ingestion, "_extract_with_pymupdf4llm", fake_fallback)

    text = extract_full_text("trial.pdf")

    assert calls == [("docling", "trial.pdf")]
    assert text == "Docling text with hyphenbreaks"


def test_extract_full_text_falls_back_to_pymupdf4llm(monkeypatch):
    calls = []

    def fake_docling(pdf_path):
        calls.append(("docling", pdf_path))
        raise RuntimeError("docling failed")

    def fake_fallback(pdf_path):
        calls.append(("fallback", pdf_path))
        return "Fallback extracted randomized trial text."

    monkeypatch.setattr(pdf_ingestion, "_extract_with_docling", fake_docling)
    monkeypatch.setattr(pdf_ingestion, "_extract_with_pymupdf4llm", fake_fallback)

    text = extract_full_text("trial.pdf")

    assert calls == [("docling", "trial.pdf"), ("fallback", "trial.pdf")]
    assert text == "Fallback extracted randomized trial text."


def test_parse_sections_detects_expected_sections():
    text = """
    ABSTR ACT
    This randomized trial compared drug A with placebo.
    Methods
    Participants were randomly assigned in a 1:1 ratio.
    Randomization
    A computer-generated randomization schedule was used.
    Blinding
    Participants and investigators were double-blind.
    Results
    The primary outcome improved.
    Trial registration
    ClinicalTrials.gov NCT00000000.
    """

    sections = parse_sections(text)

    assert "randomized trial" in sections["abstract"]
    assert "Participants were randomly assigned" in sections["methods"]
    assert "computer-generated" in sections["randomization"]
    assert "double-blind" in sections["blinding"]
    assert "primary outcome" in sections["results"]
    assert "ClinicalTrials.gov" in sections["registration"]


def test_parse_sections_detects_markdown_headings():
    text = """
    ## Methods
    Participants were randomly assigned.
    **Outcomes**
    Overall survival was the primary endpoint.
    """

    sections = parse_sections(text)

    assert "randomly assigned" in sections["methods"]
    assert "Overall survival" in sections["outcomes"]


def test_parse_sections_recovers_keyword_context_without_headings():
    text = """
    The paper describes a phase 3 trial.
    Patients were assigned to treatment groups centrally.
    Overall survival was the primary endpoint and progression-free survival was secondary.
    Analyses used the intention-to-treat population.
    """

    sections = parse_sections(text)

    assert "primary endpoint" in sections["outcomes"]
    assert "intention-to-treat" in sections["analysis"]


def test_parse_sections_falls_back_to_methods_for_randomization_and_blinding():
    text = """
    Methods
    This was a randomized double-blind controlled trial using identical placebo.
    Results
    Participants completed follow-up.
    """

    sections = parse_sections(text)

    assert sections["methods"]
    assert sections["randomization"] == sections["methods"]
    assert sections["blinding"] == sections["methods"]


def test_parse_sections_returns_empty_strings_for_missing_sections():
    sections = parse_sections("Abstract\nBrief abstract only.")

    assert set(sections) == {
        "abstract",
        "methods",
        "randomization",
        "blinding",
        "outcomes",
        "analysis",
        "results",
        "missing_data",
        "registration",
        "baseline",
        "consort",
        "supplementary",
    }
    assert sections["methods"] == ""


def test_cap_section_returns_unchanged_when_under_limit():
    text = "A" * 7999
    capped = cap_section(text)

    assert capped == text


def test_cap_section_prefers_keyword_dense_chunks():
    text = (
        "A" * 3000
        + " random allocation conceal blind " * 40
        + "B" * 3000
        + " outcome endpoint register " * 40
        + "C" * 3000
    )
    capped = cap_section(text)

    assert "[... truncated ...]" in capped
    assert "allocation" in capped.lower()
    assert "[NOTE: Section truncated at 10000 characters. Critical content may be absent.]" in capped
    assert len(capped) <= 10000 + len("\n\n[NOTE: Section truncated at 10000 characters. Critical content may be absent.]")
