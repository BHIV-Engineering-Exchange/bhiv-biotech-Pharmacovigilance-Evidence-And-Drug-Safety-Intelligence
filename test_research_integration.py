from src.research_integration import (
    validate_research_report,
    run_research_workflow,
)


def make_report():
    return {"report_id": "SYN-001", "drug_name": "  ibuprofen  "}


def test_valid_report_retrieval_and_provenance():
    def retriever(drug_name, limit=5):
        assert drug_name == "  ibuprofen  ".strip()
        assert limit == 2
        return {
            "success": True,
            "source": "OpenFDA/FAERS",
            "retrieved_at": "2026-11-22T10:00:00+00:00",
            "source_url": "https://api.fda.gov/drug/event.json",
            "record_count": 1,
            "raw_response": {
                "results": [{
                    "safetyreportid": "SRC-001",
                    "patient": {
                        "drug": [{"medicinalproduct": "IBUPROFEN"}],
                        "reaction": [{"reactionmeddrapt": "HEADACHE"}],
                    },
                }]
            },
        }

    report = make_report()
    result = run_research_workflow(report, limit=2, retriever=retriever)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["original_report"] == report
    assert result["normalized_input"]["drug_name_original"] == "  ibuprofen  "
    assert result["findings"][0]["source"]["identifier"] == "SRC-001"
    assert result["findings"][0]["evidence_origin"] == "SOURCE_DERIVED"
    assert result["human_review"]["status"] == "PENDING"


def test_invalid_report_returns_human_review_pending():
    result = run_research_workflow({"report_id": "SYN-002"})
    assert result["status"] == "INVALID_INPUT"
    assert "Missing drug_name" in result["uncertainty"]["limitations"]
    assert result["human_review"]["required"] is True


def test_missing_evidence_is_explicit():
    def retriever(drug_name, limit=5):
        return {
            "success": True,
            "retrieved_at": "2026-11-22T10:00:00+00:00",
            "source_url": "https://api.fda.gov/drug/event.json",
            "raw_response": {"results": []},
        }

    result = run_research_workflow(
        {"report_id": "SYN-003", "drug_name": "no-such-drug"},
        retriever=retriever,
    )
    assert result["status"] == "NO_EVIDENCE"
    assert result["findings"] == []
    assert "No matching source records" in result["uncertainty"]["missing_evidence"]


def test_external_source_unavailable():
    def retriever(drug_name, limit=5):
        return {"success": False, "error": "API request failed: timeout"}

    result = run_research_workflow(
        {"report_id": "SYN-004", "drug_name": "ibuprofen"},
        retriever=retriever,
    )
    assert result["status"] == "SOURCE_UNAVAILABLE"
    assert "timeout" in result["uncertainty"]["missing_evidence"]


def test_unexpected_retriever_response():
    result = run_research_workflow(
        {"report_id": "SYN-005", "drug_name": "ibuprofen"},
        retriever=lambda drug_name, limit=5: ["unexpected"],
    )
    assert result["status"] == "SOURCE_UNAVAILABLE"


def test_validation_contract():
    assert validate_research_report({"report_id": "", "drug_name": "ibuprofen"})["valid"] is False
    assert validate_research_report(make_report())["valid"] is True
