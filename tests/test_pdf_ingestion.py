import fitz

from rob2_pipeline.pdf_ingestion import cap_section, extract_full_text, parse_sections, section_debug_summary


def test_extract_full_text_from_synthetic_pdf(tmp_path):
    pdf_path = tmp_path / "synthetic_trial.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Abstract\nThis was a randomized trial.\nMethods\nPatients were allocated.")
    doc.save(pdf_path)
    doc.close()

    text = extract_full_text(str(pdf_path))

    assert "Abstract" in text
    assert "randomized trial" in text


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


def test_cap_section_keeps_first_and_last_segments():
    text = "A" * 3500 + "MIDDLE" + "B" * 3500
    capped = cap_section(text)

    assert len(capped) == 6000
    assert "[... truncated ...]" in capped
    assert capped.startswith("A" * 100)
    assert capped.endswith("B" * 100)
    assert "MIDDLE" not in capped


def test_section_debug_summary_reports_counts():
    sections = parse_sections("Abstract\nHello\nMethods\nWorld")
    debug = section_debug_summary(sections)

    assert debug["abstract"]["detected"] is True
    assert debug["abstract"]["chars"] == len(sections["abstract"])
    assert debug["results"]["detected"] is False
