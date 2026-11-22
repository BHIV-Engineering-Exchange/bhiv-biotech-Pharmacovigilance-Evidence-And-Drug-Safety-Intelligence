import json
import runpy
import pytest
from pathlib import Path

BASE = Path(__file__).parent

adapter = runpy.run_path(
    str(BASE / "drug_safety_import_adapter.py")
)

checker = runpy.run_path(
    str(BASE / "duplicate_conflict_checks.py")
)

review = runpy.run_path(
    str(BASE / "review_lifecycle.py")
)

load_input = adapter["load_producer_input"]
classify = checker["classify_records"]
create_review = review["create_review_item"]
transition = review["transition_review"]


def make_record(eid, source_id, observation, status="Validated"):
    return {
        "evidence_id": eid,
        "source": "PubMed",
        "drug_product_identifier": "Drug A",
        "evidence_type": "Literature",
        "observation": observation,
        "date": "2026-08-01",
        "validation_status": status,
        "human_review_flag": status != "Validated",
        "evidence_provenance": {
            "original_evidence_id": source_id
        }
    }


def test_01_actual_input_has_ten_records():
    wrapper, records = load_input()
    assert len(records) == 10
    assert wrapper["record_count"] == 10


def test_02_original_input_schema_is_preserved():
    wrapper, records = load_input()
    assert wrapper["schema_name"] == "BHIV_Drug_Safety_Evidence"
    assert wrapper["schema_version"] == "1.0.0"


def test_03_non_dictionary_wrapper_rejected(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setitem(load_input.__globals__, "INPUT_FILE", path)
    with pytest.raises(ValueError):
        load_input()


def test_04_missing_records_array_rejected(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text('{"record_count": 0}', encoding="utf-8")
    monkeypatch.setitem(load_input.__globals__, "INPUT_FILE", path)
    with pytest.raises(ValueError):
        load_input()


def test_05_wrong_record_count_rejected(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text(
        '{"record_count": 5, "records": []}',
        encoding="utf-8"
    )
    monkeypatch.setitem(load_input.__globals__, "INPUT_FILE", path)
    with pytest.raises(ValueError):
        load_input()


def test_06_exact_duplicate_detected():
    records = [
        make_record("A", "SRC1", "Headache"),
        make_record("B", "SRC1", "Headache")
    ]
    result = classify(records)
    assert result["A"]["duplicate_status"] == "EXACT_DUPLICATE"
    assert result["B"]["human_review_required"] is True


def test_07_same_identifier_different_content_flagged():
    records = [
        make_record("A", "SRC1", "Headache"),
        make_record("B", "SRC1", "Nausea")
    ]
    result = classify(records)
    assert result["A"]["conflict_status"] == (
        "SAME_SOURCE_ID_DIFFERENT_CONTENT"
    )


def test_08_unrelated_records_not_marked_duplicate():
    records = [
        make_record("A", "SRC1", "Headache"),
        make_record("B", "SRC2", "Nausea")
    ]
    result = classify(records)
    assert result["A"]["duplicate_status"] == "NO_DUPLICATE_DETECTED"


def test_09_producer_conflict_preserved():
    record = make_record(
        "A", "SRC1", "No clear association", "Conflicting"
    )
    result = classify([record])
    assert result["A"]["conflict_status"] == "SOURCE_REPORTED_CONFLICT"
    assert result["A"]["human_review_required"] is True


def test_10_review_requires_valid_transition_and_reviewer():
    item = create_review("EV001", "Test review")
    assert item["review_status"] == "PENDING"

    with pytest.raises(ValueError):
        transition(item, "COMPLETED", "Reviewer1")

    transition(item, "IN_REVIEW", "Reviewer1")
    assert item["review_status"] == "IN_REVIEW"


def test_11_missing_required_provenance_is_rejected():
    from src.evidence_schema import EvidenceRecord, validate_evidence

    record = EvidenceRecord(
        evidence_id="EV-TEST-001",
        drug_name="Drug A",
        drug_identifier=None,
        adverse_event=None,
        source="PubMed",
        source_record_id="SRC-001",
        evidence_type="Literature",
        event_date=None,
        retrieved_at="2026-08-01T10:00:00+00:00",
        source_url="",
        schema_version="1.1",
        provenance={
            "source_system": "PubMed",
            "underlying_dataset": "",
            "retrieval_method": "",
            "transformation": "",
        },
        raw_record_reference="test-record",
        entity_resolution_status="UNRESOLVED",
        association_type="REPORTED_ASSOCIATION",
    )

    valid, errors = validate_evidence(record)

    assert not valid
    assert "Missing source_url" in errors
    assert "Missing provenance field: underlying_dataset" in errors
    assert "Missing provenance field: retrieval_method" in errors
    assert "Missing provenance field: transformation" in errors


def test_12_unknown_drug_remains_unresolved():
    from src.entity_resolution import (
        EntityCandidate,
        UNRESOLVED,
        resolve_entity,
    )

    candidates = [
        EntityCandidate(
            canonical_name="Ibuprofen",
            identifier="TEST-IBU-001",
        )
    ]

    result = resolve_entity("Drug A", candidates)

    assert result.status == UNRESOLVED
    assert result.canonical_name is None
    assert result.identifier is None


def test_13_synthetic_data_status_remains_unknown():
    qc_path = BASE / "drug_safety_qc_report.json"

    with qc_path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    assert report["record_count"] == 10
    assert all(
        item["synthetic_data_status"] == "unknown"
        for item in report["records"]
    )


def test_14_adapter_output_is_deterministic(tmp_path, monkeypatch):
    main_globals = adapter["main"].__globals__

    monkeypatch.setitem(
        main_globals,
        "OUTPUT_FILE",
        tmp_path / "output.json",
    )
    monkeypatch.setitem(
        main_globals,
        "QC_FILE",
        tmp_path / "qc.json",
    )

    adapter["main"]()

    first_output = (tmp_path / "output.json").read_bytes()
    first_qc = (tmp_path / "qc.json").read_bytes()

    adapter["main"]()

    second_output = (tmp_path / "output.json").read_bytes()
    second_qc = (tmp_path / "qc.json").read_bytes()

    assert first_output == second_output
    assert first_qc == second_qc
