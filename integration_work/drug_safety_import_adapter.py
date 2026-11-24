import json
from pathlib import Path
from dataclasses import asdict

from src.evidence_schema import (
    EvidenceRecord,
    validate_evidence,
    generate_evidence_id,
    SCHEMA_VERSION,
    UNRESOLVED,
    REPORTED_ASSOCIATION,
)


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "drug_safety_input.json"
OUTPUT_FILE = BASE_DIR / "staged_receiver_records.json"
QC_FILE = BASE_DIR / "drug_safety_qc_report.json"


def load_producer_input():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Producer input must be a JSON wrapper.")

    records = data.get("records")

    if not isinstance(records, list):
        raise ValueError("Producer input must contain a records array.")

    if data.get("record_count") != len(records):
        raise ValueError("Declared record count does not match actual count.")

    return data, records


def convert_record(record, index):
    producer_provenance = record.get("evidence_provenance") or {}

    source_record_id = producer_provenance.get(
        "original_evidence_id"
    ) or record.get("evidence_id")

    # Proposed mapping from the integration boundary.
    retrieved_at = producer_provenance.get("ingestion_timestamp") or ""

    # Preserve source transformation details without assuming
    # that the receiver has approved their mapping.
    provenance = {
        "source_system": producer_provenance.get("original_source") or "",
        "underlying_dataset": "",
        "retrieval_method": "",
        "transformation": "",
        "producer_transformation_path": producer_provenance.get(
            "transformation_path"
        ),
        "producer_source_version": producer_provenance.get(
            "source_version"
        ),
        "original_provenance": producer_provenance,
        "source_organisation": record.get("source_organisation"),
        "mapping_status": "PROPOSED_MAPPING_PENDING_APPROVAL",
    }

    candidate = EvidenceRecord(
        evidence_id=generate_evidence_id(index, source_record_id),
        drug_name=record.get("drug_product_identifier"),
        drug_identifier=None,
        # The producer observation is retained in the raw record.
        # It is not automatically classified as an adverse event.
        adverse_event=None,
        source=record.get("source") or "",
        source_record_id=source_record_id,
        evidence_type=record.get("evidence_type") or "",
        event_date=record.get("date"),
        retrieved_at=retrieved_at,
        source_url="",
        schema_version=SCHEMA_VERSION,
        provenance=provenance,
        raw_record_reference=(
            f"drug_safety_input.json#records/{index}"
        ),
        entity_resolution_status=UNRESOLVED,
        association_type=REPORTED_ASSOCIATION,
    )

    return candidate


def main():
    wrapper, producer_records = load_producer_input()

    staged_records = []
    qc_results = []

    for index, original in enumerate(producer_records):
        candidate = convert_record(original, index)

        valid, errors = validate_evidence(candidate)

        producer_status = original.get("validation_status", "Unknown")
        producer_review = bool(original.get("human_review_flag", False))

        review_required = (
            producer_review
            or not valid
            or producer_status != "Validated"
        )

        staged_records.append({
            "receiver_candidate": asdict(candidate),
            "original_producer_record": original,
        })

        qc_results.append({
            "evidence_id": candidate.evidence_id,
            "source_record_id": candidate.source_record_id,
            "producer_evidence_id": original.get("evidence_id"),
            "producer_validation_status": producer_status,
            "receiver_validation_status": (
                "VALID" if valid else "INVALID"
            ),
            "validation_errors": errors,
            "duplicate_status": "NOT_EVALUATED",
            "conflict_status": "NOT_EVALUATED",
            "import_status": "STAGED",
            "processing_status": (
                "STAGED_FOR_REVIEW" if review_required
                else "STAGED"
            ),
            "human_review_required": review_required,
            "human_review_status": (
                "PENDING" if review_required else "NOT_REQUIRED"
            ),
            "synthetic_data_status": "unknown",
        })

    # DUPLICATE_CONFLICT_CHECKS_CONNECTED
    import runpy

    checker = runpy.run_path(
        str(BASE_DIR / "duplicate_conflict_checks.py")
    )
    classify_records = checker["classify_records"]

    relationship_results = classify_records(producer_records)

    for item in qc_results:
        producer_id = item["producer_evidence_id"]
        relationship = relationship_results.get(producer_id, {})

        item["duplicate_status"] = relationship.get(
            "duplicate_status", "NOT_EVALUATED"
        )
        item["conflict_status"] = relationship.get(
            "conflict_status", "NOT_EVALUATED"
        )
        item["related_evidence_ids"] = relationship.get(
            "related_evidence_ids", []
        )

        item["human_review_required"] = (
            item["human_review_required"]
            or relationship.get("human_review_required", False)
        )

        if item["human_review_required"]:
            item["human_review_status"] = "PENDING"
            item["processing_status"] = "STAGED_FOR_REVIEW"

    # HUMAN_REVIEW_LIFECYCLE_CONNECTED
    import runpy

    review_module = runpy.run_path(
        str(BASE_DIR / "review_lifecycle.py")
    )
    create_review_item = review_module["create_review_item"]

    for item in qc_results:
        if item["human_review_required"]:
            review_item = create_review_item(
                item["producer_evidence_id"],
                "Producer review flag, receiver validation failure, "
                "or unresolved evidence status"
            )

            item["human_review_status"] = review_item["review_status"]
            item["review_reason"] = review_item["review_reason"]
            item["reviewer_id"] = review_item["reviewer_id"]
            item["review_history"] = review_item["review_history"]
            item["workflow_completed"] = review_item["workflow_completed"]
            item["safety_confirmed"] = review_item["safety_confirmed"]
            item["causality_confirmed"] = review_item["causality_confirmed"]

    output = {
        "integration_name": "BHIV Drug Safety Staging Adapter",
        "adapter_version": "0.1.0",
        "input_schema_name": wrapper.get("schema_name"),
        "input_schema_version": wrapper.get("schema_version"),
        "receiver_schema_version": SCHEMA_VERSION,
        "record_count": len(staged_records),
        "permanent_storage_written": False,
        "records": staged_records,
    }

    qc_report = {
        "report_name": "Drug Safety Import QC Report",
        "report_version": "0.1.0",
        "record_count": len(qc_results),
        "valid_count": sum(
            item["receiver_validation_status"] == "VALID"
            for item in qc_results
        ),
        "invalid_count": sum(
            item["receiver_validation_status"] == "INVALID"
            for item in qc_results
        ),
        "human_review_count": sum(
            item["human_review_required"]
            for item in qc_results
        ),
        "duplicate_conflict_checks": "COMPLETED",
        "records": qc_results,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    QC_FILE.write_text(
        json.dumps(qc_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("DRUG SAFETY STAGING ADAPTER COMPLETED")
    print("Input records:", len(producer_records))
    print("Staged records:", len(staged_records))
    print("Receiver-valid records:", qc_report["valid_count"])
    print("Receiver-invalid records:", qc_report["invalid_count"])
    print("Human-review records:", qc_report["human_review_count"])
    print("Permanent evidence store modified: NO")
    print("Staged output:", OUTPUT_FILE)
    print("QC report:", QC_FILE)


if __name__ == "__main__":
    main()
