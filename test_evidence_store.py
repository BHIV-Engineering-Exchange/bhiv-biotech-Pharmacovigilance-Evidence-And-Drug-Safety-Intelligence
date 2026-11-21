from src import evidence_store


def make_record(
    source_record_id="FAERS-001",
    drug_name="IBUPROFEN",
    adverse_event="NAUSEA",
):
    """Create a minimal evidence record for storage tests."""

    return {
        "evidence_id": "EV-000001",
        "drug_name": drug_name,
        "drug_identifier": "NDA123456",
        "adverse_event": adverse_event,
        "source": "OpenFDA/FAERS",
        "source_record_id": source_record_id,
        "evidence_type": "FAERS adverse-event report",
        "event_date": None,
        "retrieved_at": "2026-08-31T10:00:00+00:00",
        "source_url": "https://api.fda.gov/drug/event.json",
        "schema_version": "1.1",
        "provenance": {
            "source_system": "OpenFDA",
            "underlying_dataset": "FAERS",
            "retrieval_method": "REST API",
        },
        "raw_record_reference": source_record_id,
        "entity_resolution_status": "MATCHED",
        "canonical_entity_name": "IBUPROFEN",
        "canonical_entity_identifier": "NDA123456",
        "association_type": "REPORTED_ASSOCIATION",
        "data_origin": "REAL_WORLD",
    }


def test_new_source_record_is_added(tmp_path, monkeypatch):
    evidence_file = tmp_path / "evidence_output.json"

    monkeypatch.setattr(
        evidence_store,
        "EVIDENCE_FILE",
        str(evidence_file)
    )

    record = make_record("FAERS-001")

    added = evidence_store.add_evidence([record])

    assert added == 1

    stored = evidence_store.load_evidence()

    assert len(stored) == 1
    assert stored[0]["source_record_id"] == "FAERS-001"


def test_repeated_source_record_is_not_added_twice(
    tmp_path,
    monkeypatch
):
    evidence_file = tmp_path / "evidence_output.json"

    monkeypatch.setattr(
        evidence_store,
        "EVIDENCE_FILE",
        str(evidence_file)
    )

    record = make_record("FAERS-001")

    first_added = evidence_store.add_evidence([record])
    second_added = evidence_store.add_evidence([record])

    assert first_added == 1
    assert second_added == 0

    stored = evidence_store.load_evidence()

    assert len(stored) == 1


def test_records_without_source_id_use_deterministic_fingerprint(
    tmp_path,
    monkeypatch
):
    evidence_file = tmp_path / "evidence_output.json"

    monkeypatch.setattr(
        evidence_store,
        "EVIDENCE_FILE",
        str(evidence_file)
    )

    record = make_record(
        source_record_id=None,
        drug_name="IBUPROFEN",
        adverse_event="NAUSEA"
    )

    first_added = evidence_store.add_evidence([record])
    second_added = evidence_store.add_evidence([record])

    assert first_added == 1
    assert second_added == 0

    stored = evidence_store.load_evidence()

    assert len(stored) == 1


def test_different_records_are_both_stored(
    tmp_path,
    monkeypatch
):
    evidence_file = tmp_path / "evidence_output.json"

    monkeypatch.setattr(
        evidence_store,
        "EVIDENCE_FILE",
        str(evidence_file)
    )

    record_one = make_record(
        source_record_id="FAERS-001",
        adverse_event="NAUSEA"
    )

    record_two = make_record(
        source_record_id="FAERS-002",
        adverse_event="HEADACHE"
    )

    added = evidence_store.add_evidence(
        [record_one, record_two]
    )

    assert added == 2

    stored = evidence_store.load_evidence()

    assert len(stored) == 2


def test_duplicate_records_in_same_batch_are_added_once(
    tmp_path,
    monkeypatch
):
    evidence_file = tmp_path / "evidence_output.json"

    monkeypatch.setattr(
        evidence_store,
        "EVIDENCE_FILE",
        str(evidence_file)
    )

    record = make_record("FAERS-001")

    added = evidence_store.add_evidence(
        [record, record]
    )

    assert added == 1

    stored = evidence_store.load_evidence()

    assert len(stored) == 1


def test_conflicting_payload_with_same_source_id_is_detected(
    tmp_path,
    monkeypatch
):
    evidence_file = tmp_path / "evidence_output.json"

    monkeypatch.setattr(
        evidence_store,
        "EVIDENCE_FILE",
        str(evidence_file)
    )

    record_original = make_record(
        source_record_id="FAERS-999",
        adverse_event="NAUSEA"
    )

    record_conflicting = make_record(
        source_record_id="FAERS-999",
        adverse_event="CARDIAC_ARREST"
    )

    # Store original record
    added = evidence_store.add_evidence([record_original])
    assert added == 1

    # Detect conflicts directly
    conflicts = evidence_store.detect_conflicts([record_conflicting])
    assert len(conflicts) == 1
    assert conflicts[0]["source_record_id"] == "FAERS-999"
    assert any(
        diff["field"] == "adverse_event"
        for diff in conflicts[0]["differences"]
    )

    # Audited storage surfaces the conflict distinctly from exact duplicate
    audit = evidence_store.add_evidence_with_audit([record_conflicting])
    assert audit["added"] == 0
    assert audit["conflicts"] == 1
    assert audit["duplicates"] == 0

    # Ensure store integrity is maintained
    stored = evidence_store.load_evidence()
    assert len(stored) == 1
    assert stored[0]["adverse_event"] == "NAUSEA"
