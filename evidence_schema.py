from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


SCHEMA_VERSION = "1.1"

MATCHED = "MATCHED"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"

REPORTED_ASSOCIATION = "REPORTED_ASSOCIATION"

ORIGIN_REAL_WORLD = "REAL_WORLD"
ORIGIN_SYNTHETIC = "SYNTHETIC"
ORIGIN_BENCHMARK = "BENCHMARK"
ORIGIN_TEST = "TEST"
ALLOWED_DATA_ORIGINS = {
    ORIGIN_REAL_WORLD,
    ORIGIN_SYNTHETIC,
    ORIGIN_BENCHMARK,
    ORIGIN_TEST,
}


@dataclass
class EvidenceRecord:
    evidence_id: str
    drug_name: Optional[str]
    drug_identifier: Optional[str]
    adverse_event: Optional[str]
    source: str
    source_record_id: Optional[str]
    evidence_type: str
    event_date: Optional[str]
    retrieved_at: str
    source_url: str
    schema_version: str
    provenance: Dict[str, Any]
    raw_record_reference: Optional[str]

    entity_resolution_status: str = UNRESOLVED
    canonical_entity_name: Optional[str] = None
    canonical_entity_identifier: Optional[str] = None

    association_type: str = REPORTED_ASSOCIATION
    data_origin: str = ORIGIN_REAL_WORLD

    def to_dict(self):
        return asdict(self)


def generate_evidence_id(
    index: int,
    source_record_id: Optional[str] = None
) -> str:
    """
    Generate a deterministic evidence identifier.

    A source record ID is preferred when available.
    The index is retained as a fallback.
    """

    if source_record_id:
        safe_source_id = str(source_record_id).strip()
        return f"EV-{safe_source_id}"

    return f"EV-{index:06d}"


def validate_evidence(record: EvidenceRecord):
    """Validate required evidence-integrity and type safety fields."""

    errors = []

    # Required string fields
    required_string_fields = [
        ("evidence_id", "Missing evidence_id"),
        ("source", "Missing source"),
        ("evidence_type", "Missing evidence_type"),
        ("retrieved_at", "Missing retrieved_at"),
        ("source_url", "Missing source_url"),
        ("schema_version", "Missing schema_version"),
    ]

    for attr, missing_msg in required_string_fields:
        val = getattr(record, attr, None)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(missing_msg)
        elif not isinstance(val, str):
            errors.append(f"Invalid type for {attr}: expected str, got {type(val).__name__}")

    # Optional string fields type validation
    optional_string_fields = [
        "drug_name",
        "drug_identifier",
        "adverse_event",
        "event_date",
        "source_record_id",
        "raw_record_reference",
        "canonical_entity_name",
        "canonical_entity_identifier",
    ]

    for attr in optional_string_fields:
        val = getattr(record, attr, None)
        if val is not None and not isinstance(val, str):
            errors.append(f"Invalid type for {attr}: expected str or None, got {type(val).__name__}")

    # ---------------------------------------------------------
    # Provenance validation
    # ---------------------------------------------------------

    if not isinstance(record.provenance, dict):
        errors.append("Provenance must be a dictionary")
    else:
        required_provenance_fields = [
            "source_system",
            "underlying_dataset",
            "retrieval_method",
            "transformation",
        ]

        for field in required_provenance_fields:
            value = record.provenance.get(field)
            if value is None or str(value).strip() == "":
                errors.append(f"Missing provenance field: {field}")
            elif not isinstance(value, str):
                errors.append(f"Invalid type for provenance field {field}: expected str")

    # ---------------------------------------------------------
    # Entity-resolution validation
    # ---------------------------------------------------------

    if record.entity_resolution_status not in {
        MATCHED,
        AMBIGUOUS,
        UNRESOLVED,
    }:
        errors.append(
            f"Invalid entity_resolution_status: {record.entity_resolution_status}"
        )

    # ---------------------------------------------------------
    # Association-type validation
    # ---------------------------------------------------------

    if record.association_type != REPORTED_ASSOCIATION:
        errors.append(
            f"Invalid association_type: {record.association_type}"
        )

    # ---------------------------------------------------------
    # Data-origin validation (Synthetic vs Real-world)
    # ---------------------------------------------------------

    data_origin = getattr(record, "data_origin", None)
    if not data_origin or not isinstance(data_origin, str) or not data_origin.strip():
        errors.append("Missing data_origin")
    elif data_origin not in ALLOWED_DATA_ORIGINS:
        errors.append(f"Invalid data_origin: {data_origin}")

    return len(errors) == 0, errors
