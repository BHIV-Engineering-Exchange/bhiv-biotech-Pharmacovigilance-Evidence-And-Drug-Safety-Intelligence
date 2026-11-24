"""
BHIV BiotechSystem — Shared Evidence Contract v1.0
Hariom Upadhyay | Backend Architecture & Integration | EOD 20 November 2026

Defines the versioned cross-workstream evidence contract.
This contract is NOT a clinical record. It is a software data-exchange schema.

Required fields, optional fields, accepted values and validation rules are
documented here and enforced by SharedEvidenceContract.validate().

References:
  - Canonical schema: src/evidence_schema.py (EvidenceRecord, schema_version="1.1")
  - QC engine schema: qc_engine/engine.py + schemas/evidence_qc_schema_v1.0.0.json (Shyamal)
  - Drug safety adapter: integration_work/drug_safety_import_adapter.py (Shravani)
  - Drug discovery scoring: calculate_scores_v2.py (Shamit)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Contract version
# ---------------------------------------------------------------------------

CONTRACT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Allowed enum values — keep in sync with EvidenceRecord in evidence_schema.py
# ---------------------------------------------------------------------------

ALLOWED_VALIDATION_STATUS = {
    "VALID",
    "INVALID",
    "PENDING",
    "REVIEW_REQUIRED",
}

ALLOWED_DUPLICATE_STATUS = {
    "UNIQUE",
    "EXACT_DUPLICATE",
    "NEAR_DUPLICATE",
    "UNKNOWN",
}

ALLOWED_CONFLICT_STATUS = {
    "NO_CONFLICT",
    "CONTENT_CONFLICT",
    "PROVENANCE_CONFLICT",
    "UNKNOWN",
}

ALLOWED_HUMAN_REVIEW_STATUS = {
    "NOT_REQUIRED",
    "PENDING",
    "IN_REVIEW",
    "REVIEWED",
    "REQUIRES_SECOND_REVIEW",
    "CLOSED",
}

ALLOWED_DATA_ORIGINS = {
    "REAL_WORLD",
    "SYNTHETIC",
    "BENCHMARK",
    "TEST",
}

ALLOWED_EVIDENCE_TYPES = {
    "FAERS adverse-event report",
    "Drug safety biosimilarity record",
    "Drug discovery candidate record",
    "Clinical observation",
    "Literature citation",
    "Regulatory submission",
    "Unknown",
}


# ---------------------------------------------------------------------------
# Shared Evidence Contract dataclass
# ---------------------------------------------------------------------------

@dataclass
class SharedEvidenceContract:
    """
    Versioned cross-workstream evidence interchange record.

    REQUIRED fields (must not be None or empty):
      - evidence_id
      - source_record_id
      - source
      - source_url (must be non-empty; use "" only where documented as BLOCKER)
      - drug_name
      - evidence_type
      - retrieved_at
      - schema_version
      - provenance (dict with at minimum source_system key)
      - data_origin
      - validation_status
      - duplicate_status
      - conflict_status
      - human_review_status
      - contract_version

    OPTIONAL fields (may be None):
      - drug_identifier
      - event_date
      - adverse_event
      - qc_status
      - qc_errors
      - producer_record (original producer data, preserved verbatim)
      - producer_validation_status (producer's own status string)
      - entity_resolution_status
      - canonical_entity_name
      - association_type
      - notes
    """

    # --- Required ---
    evidence_id: str
    source_record_id: str
    source: str
    source_url: str
    drug_name: str
    evidence_type: str
    retrieved_at: str
    schema_version: str
    provenance: Dict[str, Any]
    data_origin: str
    validation_status: str
    duplicate_status: str
    conflict_status: str
    human_review_status: str
    contract_version: str = CONTRACT_VERSION

    # --- Optional ---
    drug_identifier: Optional[str] = None
    event_date: Optional[str] = None
    adverse_event: Optional[str] = None

    qc_status: Optional[str] = None
    qc_errors: Optional[List[str]] = None

    # Preserved verbatim from the upstream producer.
    # Must NOT be modified by integration layers.
    producer_record: Optional[Dict[str, Any]] = None
    producer_validation_status: Optional[str] = None

    entity_resolution_status: Optional[str] = None
    canonical_entity_name: Optional[str] = None
    association_type: Optional[str] = None

    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        """
        Deterministic SHA-256 fingerprint of content fields.
        Used for exact-duplicate detection across workstreams.
        """
        fp_data = {
            "drug_name": self.drug_name,
            "drug_identifier": self.drug_identifier,
            "adverse_event": self.adverse_event,
            "source": self.source,
            "evidence_type": self.evidence_type,
            "event_date": self.event_date,
            "data_origin": self.data_origin,
        }
        canonical = json.dumps(fp_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate required fields, enum values and type constraints.
        Returns (is_valid: bool, errors: List[str]).
        """
        errors: List[str] = []

        # Required non-empty strings
        required_strings = [
            ("evidence_id", self.evidence_id),
            ("source_record_id", self.source_record_id),
            ("source", self.source),
            ("drug_name", self.drug_name),
            ("evidence_type", self.evidence_type),
            ("retrieved_at", self.retrieved_at),
            ("schema_version", self.schema_version),
            ("data_origin", self.data_origin),
            ("validation_status", self.validation_status),
            ("duplicate_status", self.duplicate_status),
            ("conflict_status", self.conflict_status),
            ("human_review_status", self.human_review_status),
            ("contract_version", self.contract_version),
        ]
        for attr, val in required_strings:
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(f"Missing required field: {attr}")
            elif not isinstance(val, str):
                errors.append(f"Field {attr} must be str, got {type(val).__name__}")

        # source_url: required but may be empty string with explicit BLOCKER note
        if self.source_url is None:
            errors.append("source_url must not be None (use empty string with blocker note)")

        # Provenance dict
        if not isinstance(self.provenance, dict):
            errors.append("provenance must be a dict")
        else:
            if not self.provenance.get("source_system"):
                errors.append("provenance.source_system is required")

        # Enum checks
        enum_checks = [
            ("data_origin", self.data_origin, ALLOWED_DATA_ORIGINS),
            ("validation_status", self.validation_status, ALLOWED_VALIDATION_STATUS),
            ("duplicate_status", self.duplicate_status, ALLOWED_DUPLICATE_STATUS),
            ("conflict_status", self.conflict_status, ALLOWED_CONFLICT_STATUS),
            ("human_review_status", self.human_review_status, ALLOWED_HUMAN_REVIEW_STATUS),
        ]
        for attr, val, allowed in enum_checks:
            if isinstance(val, str) and val and val not in allowed:
                errors.append(
                    f"Invalid value for {attr}: '{val}'. Allowed: {sorted(allowed)}"
                )

        # Optional string type checks
        optional_strings = [
            "drug_identifier",
            "event_date",
            "adverse_event",
            "qc_status",
            "entity_resolution_status",
            "canonical_entity_name",
            "association_type",
            "notes",
            "producer_validation_status",
        ]
        for attr in optional_strings:
            val = getattr(self, attr, None)
            if val is not None and not isinstance(val, str):
                errors.append(f"Optional field {attr} must be str or None, got {type(val).__name__}")

        # qc_errors must be list or None
        if self.qc_errors is not None and not isinstance(self.qc_errors, list):
            errors.append("qc_errors must be a list or None")

        # producer_record must be dict or None
        if self.producer_record is not None and not isinstance(self.producer_record, dict):
            errors.append("producer_record must be a dict or None")

        return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Factory — build from EvidenceRecord (Jaydeep/Hariom canonical schema)
# ---------------------------------------------------------------------------

def from_evidence_record(
    record_dict: Dict[str, Any],
    validation_status: str = "VALID",
    duplicate_status: str = "UNIQUE",
    conflict_status: str = "NO_CONFLICT",
    human_review_status: str = "PENDING",
    producer_record: Optional[Dict[str, Any]] = None,
    producer_validation_status: Optional[str] = None,
    qc_status: Optional[str] = None,
    qc_errors: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> SharedEvidenceContract:
    """
    Build a SharedEvidenceContract from an EvidenceRecord dict
    (output of EvidenceRecord.to_dict()).

    Does NOT fabricate missing fields — leaves them as None.
    """
    return SharedEvidenceContract(
        evidence_id=record_dict.get("evidence_id", ""),
        source_record_id=record_dict.get("source_record_id") or record_dict.get("evidence_id", ""),
        source=record_dict.get("source", ""),
        source_url=record_dict.get("source_url") or "",
        drug_name=record_dict.get("drug_name") or "",
        drug_identifier=record_dict.get("drug_identifier"),
        evidence_type=record_dict.get("evidence_type", ""),
        event_date=record_dict.get("event_date"),
        retrieved_at=record_dict.get("retrieved_at", ""),
        schema_version=record_dict.get("schema_version", ""),
        provenance=record_dict.get("provenance") or {"source_system": ""},
        data_origin=record_dict.get("data_origin", "REAL_WORLD"),
        adverse_event=record_dict.get("adverse_event"),
        validation_status=validation_status,
        duplicate_status=duplicate_status,
        conflict_status=conflict_status,
        human_review_status=human_review_status,
        entity_resolution_status=record_dict.get("entity_resolution_status"),
        canonical_entity_name=record_dict.get("canonical_entity_name"),
        association_type=record_dict.get("association_type"),
        producer_record=producer_record,
        producer_validation_status=producer_validation_status,
        qc_status=qc_status,
        qc_errors=qc_errors,
        notes=notes,
        contract_version=CONTRACT_VERSION,
    )
