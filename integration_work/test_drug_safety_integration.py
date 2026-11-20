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


