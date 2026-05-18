import rob2_pipeline.pdf_ingestion as pdf_ingestion
from rob2_pipeline.models import empty_paper_evidence, format_evidence
from rob2_pipeline.nodes.ingest import pdf_ingest_node
from rob2_pipeline.pdf_ingestion import (
    _build_docling_chunks,
    build_document_repr,
    cap_section,
    extract_censoring_context,
    extract_full_text,
    extract_paper_evidence,
    extract_structural_paper_evidence,
    parse_sections,
)
from rob2_pipeline.providers.base import LLMResponse


def test_extract_full_text_uses_docling(monkeypatch):
    calls = []

    def fake_docling(pdf_path):
        calls.append(("docling", pdf_path))
        return "Docling text\xa0with hyphen-\nbreaks"

    monkeypatch.setattr(pdf_ingestion, "_extract_with_docling", fake_docling)

    text = extract_full_text("trial.pdf")

    assert calls == [("docling", "trial.pdf")]
    assert text == "Docling text with hyphenbreaks"


def test_extract_full_text_raises_when_docling_fails(monkeypatch):
    """Single-path docling: if docling fails, the exception propagates up. No
    silent fallback to a different parser."""
    def fake_docling(pdf_path):
        raise RuntimeError("docling exploded")

    monkeypatch.setattr(pdf_ingestion, "_extract_with_docling", fake_docling)

    try:
        extract_full_text("trial.pdf")
    except RuntimeError as error:
        assert "docling exploded" in str(error)
    else:
        raise AssertionError("extract_full_text should raise when docling fails")


def _make_mock_chunk(text: str, headings: list[str], pages: list[int]):
    class MockMeta:
        def __init__(self):
            self.headings = headings
            self.page_numbers = pages

        def export_json_dict(self):
            return {"headings": headings, "page_numbers": pages}

    class MockChunk:
        def __init__(self):
            self.text = text
            self.meta = MockMeta()

    return MockChunk()


def test_build_docling_chunks_returns_langchain_documents(monkeypatch):
    mock_conv = type("ConversionResult", (), {"document": object()})()
    mock_chunks = [
        _make_mock_chunk("Patients were randomly allocated.", ["Methods"], [2]),
        _make_mock_chunk("Allocation was concealed.", ["Methods"], [2]),
        _make_mock_chunk("Baseline characteristics.", ["Baseline"], [3]),
    ]

    class MockChunker:
        def __init__(self, tokenizer):
            self.tokenizer = tokenizer

        def chunk(self, document):
            return mock_chunks

    monkeypatch.setattr(pdf_ingestion, "HybridChunker", MockChunker)

    result = _build_docling_chunks(mock_conv)

    assert len(result) == 3
    assert all(doc.page_content for doc in result)


def test_build_docling_chunks_preserves_metadata(monkeypatch):
    mock_conv = type("ConversionResult", (), {"document": object()})()
    mock_chunks = [_make_mock_chunk("Text about randomization.", ["Methods"], [2])]

    class MockChunker:
        def __init__(self, tokenizer):
            self.tokenizer = tokenizer

        def chunk(self, document):
            return mock_chunks

    monkeypatch.setattr(pdf_ingestion, "HybridChunker", MockChunker)

    result = _build_docling_chunks(mock_conv)

    assert result[0].metadata["section"] == "Methods"
    assert result[0].metadata["page_numbers"] == [2]
    assert result[0].metadata["dl_meta"] == {"headings": ["Methods"], "page_numbers": [2]}


def test_build_docling_chunks_handles_no_headings(monkeypatch):
    mock_conv = type("ConversionResult", (), {"document": object()})()
    mock_chunks = [_make_mock_chunk("Plain text.", [], [1])]

    class MockChunker:
        def __init__(self, tokenizer):
            self.tokenizer = tokenizer

        def chunk(self, document):
            return mock_chunks

    monkeypatch.setattr(pdf_ingestion, "HybridChunker", MockChunker)

    result = _build_docling_chunks(mock_conv)

    assert result[0].metadata["section"] == ""


def test_build_docling_chunks_configures_tokenizer_for_long_docling_counts(monkeypatch):
    mock_conv = type("ConversionResult", (), {"document": object()})()
    mock_chunks = [_make_mock_chunk("Text about randomization.", ["Methods"], [2])]
    tokenizer_calls = []

    class MockTokenizer:
        @classmethod
        def from_pretrained(cls, model_name, **kwargs):
            tokenizer_calls.append((model_name, kwargs))
            return "configured-tokenizer"

    class MockChunker:
        def __init__(self, tokenizer):
            self.tokenizer = tokenizer

        def chunk(self, document):
            assert self.tokenizer == "configured-tokenizer"
            return mock_chunks

    monkeypatch.setattr(pdf_ingestion, "HuggingFaceTokenizer", MockTokenizer, raising=False)
    monkeypatch.setattr(pdf_ingestion, "HybridChunker", MockChunker)

    result = _build_docling_chunks(mock_conv)

    assert tokenizer_calls == [
        (
            "BAAI/bge-small-en-v1.5",
            {"max_tokens": 256, "model_max_length": 10**9},
        )
    ]
    assert result[0].page_content == "Text about randomization."
    assert result[0].metadata["section"] == "Methods"
    assert result[0].metadata["page_numbers"] == [2]


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


def test_ingest_node_raises_when_docling_converter_fails(monkeypatch):
    """Single-path docling: if the docling converter fails, the exception
    propagates and the run halts. No silent fallback to text-keyword parsing."""
    known_text = "Methods\nParticipants were randomly assigned in a 1:1 ratio.\nResults\nDone."
    monkeypatch.setattr("rob2_pipeline.nodes.ingest.extract_full_text", lambda _: known_text)

    class BrokenConverter:
        def convert(self, _):
            raise RuntimeError("docling structured parse failed")

    monkeypatch.setattr("rob2_pipeline.nodes.ingest._get_docling_converter", lambda use_ocr: BrokenConverter())

    state = {"pdf_path": "trial.pdf"}
    try:
        pdf_ingest_node(state)
    except RuntimeError as error:
        assert "docling structured parse failed" in str(error)
    else:
        raise AssertionError("pdf_ingest_node should raise when docling converter fails")


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
    monkeypatch.setattr("rob2_pipeline.nodes.ingest._build_docling_chunks", lambda conv_result: ["chunk"])

    result = pdf_ingest_node({"pdf_path": "trial.pdf"})

    assert result["docling_doc"] is converter.conversion_result
    assert result["docling_chunks"] == ["chunk"]


def test_ingest_node_skips_remote_extraction_when_disabled(monkeypatch):
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
    monkeypatch.setattr("rob2_pipeline.nodes.ingest.allow_remote_evidence_extraction", lambda: False)
    monkeypatch.setattr("rob2_pipeline.nodes.ingest._build_docling_chunks", lambda conv_result: ["chunk"])

    def fail_if_called(_doc_repr):
        raise AssertionError("remote extraction should be skipped when disabled")

    monkeypatch.setattr("rob2_pipeline.nodes.ingest.extract_paper_evidence", fail_if_called)

    result = pdf_ingest_node({"pdf_path": "trial.pdf"})

    assert result["evidence"]["extraction_method"] == "docling_struct"
    assert result["docling_chunks"] == ["chunk"]


def test_ingest_node_skips_remote_extraction_for_apparent_non_rct(monkeypatch):
    known_text = "Editorial commentary describing mechanism without any trial assignment."
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
    monkeypatch.setattr("rob2_pipeline.nodes.ingest.allow_remote_evidence_extraction", lambda: True)
    monkeypatch.setattr("rob2_pipeline.nodes.ingest._build_docling_chunks", lambda conv_result: ["chunk"])

    def fail_if_called(_doc_repr):
        raise AssertionError("remote extraction should be skipped for apparent non-RCT text")

    monkeypatch.setattr("rob2_pipeline.nodes.ingest.extract_paper_evidence", fail_if_called)

    result = pdf_ingest_node({"pdf_path": "trial.pdf"})

    assert result["evidence"]["extraction_method"] == "docling_struct"
    assert result["docling_chunks"] == ["chunk"]
