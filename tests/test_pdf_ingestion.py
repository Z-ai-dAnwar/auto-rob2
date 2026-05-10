import fitz

import rob2_pipeline.pdf_ingestion as pdf_ingestion
from rob2_pipeline.models import empty_paper_evidence, format_evidence
from rob2_pipeline.nodes.ingest import pdf_ingest_node
from rob2_pipeline.pdf_ingestion import (
    build_document_repr,
    cap_section,
    extract_censoring_context,
    extract_full_text,
    extract_paper_evidence,
    extract_structural_paper_evidence,
    parse_sections,
)
from rob2_pipeline.providers.base import LLMResponse


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


def test_parse_sections_from_docling_document_routes_correctly():
    class MockItem:
        def __init__(self, label, text="", table_md=""):
            self.label = label
            self.text = text
            self._table_md = table_md

        def export_to_markdown(self, doc=None):
            return self._table_md

    class MockDoc:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            for item in self._items:
                yield item, 1

        def export_to_text(self):
            return "\n".join(getattr(item, "text", "") for item in self._items)

    items = [
        MockItem("section_header", text="Methods"),
        MockItem("text", text="Patients were randomly assigned in a 1:1 ratio."),
        MockItem("section_header", text="Randomization"),
        MockItem("text", text="Computer-generated sequence was used."),
        MockItem("table", table_md="| baseline characteristics | age |\n|---|---|"),
    ]
    sections = pdf_ingestion._parse_sections_from_docling_document(MockDoc(items))

    assert sections is not None
    assert "randomly assigned" in sections["methods"]
    assert "Computer-generated" in sections["randomization"]
    assert "baseline characteristics" in sections["baseline"]


def test_build_document_repr_groups_text_and_tables_by_heading():
    class MockItem:
        def __init__(self, label, text="", table_md=""):
            self.label = label
            self.text = text
            self._table_md = table_md

        def export_to_markdown(self, doc=None):
            return self._table_md

    class MockDoc:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            for item in self._items:
                yield item, 1

        def export_to_markdown(self):
            return "# Methods\nPatients were randomized.\n| baseline | age |"

    doc_repr = build_document_repr(
        MockDoc(
            [
                MockItem("section_header", text="Methods"),
                MockItem("text", text="Patients were randomized centrally."),
                MockItem("table", table_md="| baseline characteristics | age |\n|---|---|"),
                MockItem("section_header", text="Results"),
                MockItem("paragraph", text="All randomized participants were analysed."),
            ]
        )
    )

    assert doc_repr.full_text.startswith("# Methods")
    assert doc_repr.blocks[0].heading == "Methods"
    assert "randomized centrally" in doc_repr.blocks[0].text
    assert doc_repr.blocks[0].tables == ["| baseline characteristics | age |\n|---|---|"]
    assert doc_repr.blocks[1].heading == "Results"
    assert "All randomized" in doc_repr.to_prompt_repr()
    assert "[TABLE]" in doc_repr.to_prompt_repr()


def test_extract_paper_evidence_parses_llm_xml(monkeypatch):
    class FakeProvider:
        def complete(self, system, user):
            assert "<paper>" in user
            return LLMResponse(
                """
                <evidence>
                  <abstract><text>Trial abstract.</text><tables></tables></abstract>
                  <methods><text>Randomized methods.</text><tables></tables></methods>
                  <results><text>Result text.</text><tables>| result |</tables></results>
                  <d1_randomization><text>Central sequence.</text><tables></tables></d1_randomization>
                  <d2_blinding><text>Double blind.</text><tables></tables></d2_blinding>
                  <d3_missing_data><text>Complete follow-up.</text><tables></tables></d3_missing_data>
                  <d4_outcome_meas><text>Mortality outcome.</text><tables></tables></d4_outcome_meas>
                  <d5_registration><text>NCT00000000.</text><tables></tables></d5_registration>
                  <consort_flow><text>100 randomized.</text><tables></tables></consort_flow>
                  <baseline_table><text></text><tables>| baseline | age |</tables></baseline_table>
                </evidence>
                """,
                "test-model",
                10,
                20,
                1.0,
            )

    monkeypatch.setattr(pdf_ingestion, "build_provider", lambda: FakeProvider())
    doc_repr = pdf_ingestion.DocumentRepr(
        blocks=[],
        full_text="Methods\nPatients were randomized.",
    )

    evidence, log = extract_paper_evidence(doc_repr)

    assert evidence["extraction_method"] == "docling_llm"
    assert evidence["d1_randomization"]["text"] == "Central sequence."
    assert evidence["baseline_table"]["tables"] == ["| baseline | age |"]
    assert format_evidence(evidence["results"]) == "Result text.\n\n| result |"
    assert log[0]["node"] == "paper_evidence_extraction"


def test_structural_paper_evidence_preserves_tables_by_heading():
    doc_repr = pdf_ingestion.DocumentRepr(
        blocks=[
            pdf_ingestion.DocBlock(
                heading="Baseline characteristics",
                level=2,
                text="Baseline table caption.",
                tables=["| baseline characteristics | age |\n|---|---|"],
                page_start=1,
            ),
            pdf_ingestion.DocBlock(
                heading="Participant flow",
                level=2,
                text="100 participants were randomized.",
                tables=["| randomized | analysed |\n|---|---|"],
                page_start=2,
            ),
        ],
        full_text="",
    )

    evidence = extract_structural_paper_evidence(doc_repr)

    assert evidence["extraction_method"] == "docling_struct"
    assert evidence["baseline_table"]["tables"] == ["| baseline characteristics | age |\n|---|---|"]
    assert evidence["consort_flow"]["tables"] == ["| randomized | analysed |\n|---|---|"]


def test_extract_censoring_context_finds_event_sentences():
    full_text = "\n".join(
        [
            "Introduction line.",
            "Irrelevant details.",
            "At final analysis, 415 events were observed in 917 participants.",
            "More methods text.",
            "The study reports data maturity of 74% at the data cutoff.",
            "Conclusion line.",
        ]
    )
    result = extract_censoring_context(full_text, "Overall Survival")

    assert "415 events" in result
    assert "74%" in result
    assert result
    assert len(result) <= 2000


def test_extract_censoring_context_returns_empty_for_no_matches():
    full_text = "This study compared two interventions. Outcomes improved with treatment."
    assert extract_censoring_context(full_text, "Overall Survival") == ""


def test_ingest_node_falls_back_to_text_parse_when_docling_structure_fails(monkeypatch):
    known_text = "Methods\nParticipants were randomly assigned in a 1:1 ratio.\nResults\nDone."
    monkeypatch.setattr("rob2_pipeline.nodes.ingest.extract_full_text", lambda _: known_text)

    class BrokenConverter:
        def convert(self, _):
            raise RuntimeError("docling structured parse failed")

    monkeypatch.setattr("rob2_pipeline.nodes.ingest._get_docling_converter", lambda use_ocr: BrokenConverter())

    state = {"pdf_path": "trial.pdf"}
    result = pdf_ingest_node(state)

    assert "evidence" in result
    assert result["evidence"]["extraction_method"] == "fallback"
    assert result["docling_doc"] is None
    assert "randomly assigned" in result["evidence"]["methods"]["text"]
    assert "randomly assigned" in result["evidence"]["d1_randomization"]["text"]


def test_ingest_node_stores_docling_conversion_result(monkeypatch):
    known_text = "Methods\nParticipants were randomly assigned."
    monkeypatch.setattr("rob2_pipeline.nodes.ingest.extract_full_text", lambda _: known_text)

    class MockConverter:
        def __init__(self):
            self.conversion_result = type("ConversionResult", (), {"document": object()})()

        def convert(self, _):
            return self.conversion_result

    converter = MockConverter()
    monkeypatch.setattr("rob2_pipeline.nodes.ingest._get_docling_converter", lambda use_ocr: converter)
    monkeypatch.setattr(
        "rob2_pipeline.nodes.ingest.build_document_repr",
        lambda doc: pdf_ingestion.DocumentRepr(blocks=[], full_text=known_text),
    )
    monkeypatch.setattr(
        "rob2_pipeline.nodes.ingest.extract_paper_evidence",
        lambda doc_repr: (empty_paper_evidence("docling_llm"), []),
    )

    result = pdf_ingest_node({"pdf_path": "trial.pdf"})

    assert result["docling_doc"] is converter.conversion_result
