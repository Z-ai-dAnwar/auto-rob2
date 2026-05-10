import numpy as np


def test_chunk_docling_doc_uses_sections_tables_and_splits_long_text():
    from rob2_pipeline.rag import chunk_docling_doc

    class MockItem:
        def __init__(self, label, text="", table_md=""):
            self.label = label
            self.text = text
            self._table_md = table_md

        def export_to_markdown(self, doc=None):
            return self._table_md

    class MockDoc:
        def iterate_items(self):
            yield MockItem("section_header", "Methods"), 1
            yield MockItem("text", "Short."), 1
            yield MockItem("paragraph", "Patients were randomized centrally."), 1
            yield MockItem("table", table_md="| baseline | age |\n|---|---|"), 1
            yield MockItem("section_header", "Results"), 1
            yield MockItem("text", "Sentence one. " * 180), 1

    conv_result = type("ConversionResult", (), {"document": MockDoc()})()

    chunks = chunk_docling_doc(conv_result)

    assert chunks
    assert all(set(chunk) == {"text", "section", "idx"} for chunk in chunks)
    assert all(len(chunk["text"]) <= 2000 for chunk in chunks)
    assert chunks[0]["section"] == "Methods"
    assert "Methods" in chunks[0]["text"]
    assert "Short." in chunks[0]["text"]
    assert any("| baseline | age |" in chunk["text"] for chunk in chunks)
    assert any(chunk["section"] == "Results" for chunk in chunks)


def test_build_index_and_retrieve_deduplicate_and_cap(monkeypatch):
    import rob2_pipeline.rag as rag

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            assert normalize_embeddings is True
            vectors = []
            for text in texts:
                lowered = text.lower()
                if "random" in lowered or "allocation" in lowered:
                    vectors.append([1.0, 0.0])
                elif "blinding" in lowered:
                    vectors.append([0.0, 1.0])
                else:
                    vectors.append([0.7, 0.7])
            return np.asarray(vectors, dtype="float32")

    monkeypatch.setattr(rag, "_get_model", lambda: FakeModel())

    chunks = [
        {"text": "Random allocation was central.", "section": "Methods", "idx": 0},
        {"text": "Blinding used identical placebo.", "section": "Methods", "idx": 1},
        {"text": "Randomization was concealed.", "section": "Methods", "idx": 2},
    ]

    index, indexed_chunks = rag.build_index(chunks)
    result = rag.retrieve(index, indexed_chunks, ["random allocation", "allocation concealment"], top_k=2, cap=75)

    assert index.ntotal == len(chunks)
    assert result.count("Random allocation") == 1
    assert "Randomization" in result
    assert len(result) <= 75
