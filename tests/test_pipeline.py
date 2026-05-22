from rob2_pipeline.pipeline import _assessment_json


def test_assessment_json_includes_supplement_fields():
    state = {
        "pdf_path": "paper.pdf",
        "supplementary_paths": ["protocol.pdf"],
        "source_documents": [
            {
                "document_id": "supplement:001",
                "document_name": "protocol.pdf",
                "document_role": "protocol",
                "status": "parsed",
            }
        ],
        "supplement_warnings": [],
        "rag_chunk_metadata": {},
    }

    data = _assessment_json(state)

    assert data["supplementary_paths"] == ["protocol.pdf"]
    assert data["source_documents"][0]["document_name"] == "protocol.pdf"
    assert data["supplement_warnings"] == []
