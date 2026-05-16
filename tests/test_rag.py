"""Tests for the LangChain FAISS-backed RAG module."""

import pytest
from langchain_core.documents import Document

import rob2_pipeline.rag as rag
from rob2_pipeline.rag import build_filtered_index, build_index, retrieve_adaptive


def _make_doc(text: str, section: str = "", pages: list[int] | None = None) -> Document:
    return Document(
        page_content=text,
        metadata={"section": section, "page_numbers": pages or []},
    )


@pytest.fixture()
def sample_docs():
    return [
        _make_doc("Patients were randomly allocated using computer-generated numbers.", "Methods", [2]),
        _make_doc("Allocation was concealed using sealed opaque envelopes.", "Methods", [2]),
        _make_doc("Baseline characteristics were balanced between arms.", "Baseline", [3]),
        _make_doc("All participants and personnel were blinded to treatment.", "Methods", [4]),
        _make_doc("Follow-up was complete in 95% of patients.", "Results", [8]),
        _make_doc("The trial was registered at ClinicalTrials.gov NCT12345.", "Registration", [1]),
        _make_doc("Missing data were handled using multiple imputation.", "Statistical Analysis", [5]),
        _make_doc("The primary outcome was overall survival.", "Methods", [2]),
    ]


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    class FakeEmbeddings:
        def _vector(self, text: str) -> list[float]:
            lowered = text.lower()
            return [
                float("random" in lowered or "allocat" in lowered or "conceal" in lowered),
                float("blind" in lowered or "mask" in lowered),
                float("missing" in lowered or "follow" in lowered),
                float("registr" in lowered or "nct" in lowered),
            ]

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [self._vector(text) for text in texts]

        def embed_query(self, text: str) -> list[float]:
            return self._vector(text)

        def __call__(self, text: str) -> list[float]:
            return self.embed_query(text)

    monkeypatch.setattr(rag, "_embeddings", FakeEmbeddings())


class TestBuildIndex:
    def test_builds_faiss_index_from_docs(self, sample_docs):
        index = build_index(sample_docs)

        assert index is not None

    def test_raises_on_empty_docs(self):
        with pytest.raises(ValueError, match="empty"):
            build_index([])

    def test_index_is_searchable(self, sample_docs):
        index = build_index(sample_docs)
        results = index.similarity_search("randomization method", k=2)

        assert len(results) == 2
        assert any("random" in result.page_content.lower() for result in results)


class TestBuildFilteredIndex:
    def test_filters_by_section_keyword(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["method"])

        assert filtered is not None
        results = filtered.similarity_search("randomization", k=10)
        for result in results:
            assert "method" in result.metadata.get("section", "").lower()

    def test_returns_none_when_fewer_than_3_matches(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["registration"])

        assert filtered is None

    def test_returns_none_on_no_matches(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["xyznonexistent"])

        assert filtered is None

    def test_returns_index_with_3_or_more_matches(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["method", "baseline"])

        assert filtered is not None


class TestRetrieveAdaptive:
    def test_returns_text_and_metadata(self, sample_docs):
        index = build_index(sample_docs)
        text, metas = retrieve_adaptive(index, None, ["randomization sequence generation"])

        assert isinstance(text, str)
        assert len(text) > 0
        assert isinstance(metas, list)
        assert len(metas) > 0

    def test_metadata_has_required_fields(self, sample_docs):
        index = build_index(sample_docs)
        _, metas = retrieve_adaptive(index, None, ["randomization"])

        for meta in metas:
            assert "text" in meta
            assert "section" in meta
            assert "page_numbers" in meta
            assert "score" in meta

    def test_respects_token_budget(self, sample_docs):
        index = build_index(sample_docs)
        text_small, _ = retrieve_adaptive(index, None, ["trial"], token_budget=50)
        text_large, _ = retrieve_adaptive(index, None, ["trial"], token_budget=2000)

        assert len(text_small) <= len(text_large)

    def test_uses_filtered_index_when_provided(self, sample_docs):
        index = build_index(sample_docs)
        filtered = build_filtered_index(sample_docs, keywords=["method"])
        _, metas = retrieve_adaptive(index, filtered, ["randomization"])

        for meta in metas:
            assert "method" in meta["section"].lower()

    def test_falls_back_to_full_index_when_filtered_is_none(self, sample_docs):
        index = build_index(sample_docs)
        _, metas = retrieve_adaptive(index, None, ["follow-up"])

        assert len(metas) > 0

    def test_deduplicates_results_across_queries(self, sample_docs):
        index = build_index(sample_docs)
        _, metas = retrieve_adaptive(
            index,
            None,
            ["randomization sequence generation", "random allocation sequence"],
        )
        texts = [meta["text"] for meta in metas]

        assert len(texts) == len(set(texts))
