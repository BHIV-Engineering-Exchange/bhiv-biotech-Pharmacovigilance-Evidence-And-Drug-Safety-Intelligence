"""
BHIV BiotechSystem — Patient Data & Clinical Intake Adapter
Hariom Upadhyay | Backend Architecture & Integration
Technical Convergence Baseline

Implements secure patient clinical observation intake:
- PII sanitization and pseudonymization (HIPAA/GDPR compliance boundary)
- Validation of clinical intake reports
- Mapping to SharedEvidenceContract
- Preclinical/Clinical QC validation via Shyamal's QC Engine
- Audit-backed persistence via evidence_store
- Mandatory human-review gating for clinical safety
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.evidence_schema import EvidenceRecord, validate_evidence, generate_evidence_id
from src.normalize_evidence import normalize_record
from src.evidence_store import add_evidence_with_audit, load_evidence
from src.monitoring import log_event

from integration.shared_evidence_contract import (
    CONTRACT_VERSION,
    SharedEvidenceContract,
    from_evidence_record,
)
from integration.qc_adapter import (
    build_qc_record_from_contract,
    validate_qc_record,
)

# Salt for deterministic pseudonymization without exposing patient MRN/PII
_PSEUDONYMIZATION_SALT = "BHIV_PATIENT_SAFETY_2026"


def sanitize_patient_identifier(raw_id: Optional[str]) -> str:
    """
    Hash patient identifier deterministically to protect patient privacy (PII boundary).
    Direct MRNs, national IDs, or patient names are NEVER stored in plain text.
    """
    if not raw_id or not str(raw_id).strip():
        return "ANONYMOUS_PATIENT"
    salted = f"{_PSEUDONYMIZATION_SALT}:{str(raw_id).strip()}"
    return f"PT-{hashlib.sha256(salted.encode('utf-8')).hexdigest()[:12].upper()}"


def validate_patient_intake_payload(payload: Any) -> Tuple[bool, List[str]]:
    """
    Validate incoming clinical intake report payload before ingestion.
    """
    if not isinstance(payload, dict):
        return False, ["Payload must be a dictionary."]

    errors = []
    report_id = payload.get("report_id")
    drug_name = payload.get("drug_name")

    if not report_id or not str(report_id).strip():
        errors.append("Missing required field: report_id")
    if not drug_name or not str(drug_name).strip():
        errors.append("Missing required field: drug_name")

    # Reject direct obvious PII keys
    disallowed_pii_keys = {"ssn", "social_security_number", "passport", "credit_card", "full_name"}
    found_pii = [k for k in payload.keys() if k.lower() in disallowed_pii_keys]
    if found_pii:
        errors.append(f"Direct PII fields are strictly forbidden: {found_pii}")

    return len(errors) == 0, errors


def process_patient_intake(
    payload: Dict[str, Any],
    store_evidence: bool = True,
) -> Dict[str, Any]:
    """
    Process clinical patient observation intake end-to-end:
      1. Validate intake payload
      2. Sanitize and pseudonymize patient identity
      3. Normalize into SharedEvidenceContract
      4. Validate through Shyamal's QC Engine
      5. Optionally persist to evidence_store with audit logging
      6. Enforce mandatory human-review routing
    """
    is_valid, errors = validate_patient_intake_payload(payload)
    if not is_valid:
        log_event("PATIENT_INTAKE_REJECTED", errors=errors)
        return {
            "status": "REJECTED",
            "errors": errors,
            "contract": None,
            "qc_result": None,
            "stored": False,
            "human_review_required": True,
        }

    report_id = str(payload["report_id"]).strip()
    drug_name = str(payload["drug_name"]).strip()
    adverse_event = str(payload.get("adverse_event") or payload.get("reaction") or "UNSPECIFIED_OBSERVATION").strip()
    raw_patient_id = payload.get("patient_id") or payload.get("patient_identifier")
    pseudonymized_patient = sanitize_patient_identifier(raw_patient_id)
    data_origin = payload.get("data_origin", "REAL_WORLD")

    log_event("PATIENT_INTAKE_PROCESSING", report_id=report_id, drug_name=drug_name)

    # 1. Build canonical EvidenceRecord representation
    retrieved_at = datetime.now(timezone.utc).isoformat()
    source_url = f"https://bhiv.local/clinical/patient-intake/{report_id}"

    provenance = {
        "source_system": "BHIV_Clinical_Patient_Portal",
        "underlying_dataset": "Patient_Observation_Intake",
        "retrieval_method": "CLINICAL_PORTAL_INGEST",
        "transformation": "Sanitized patient report -> SharedEvidenceContract v1.0",
        "pseudonymized_patient_id": pseudonymized_patient,
    }

    evidence_dict = {
        "evidence_id": f"EV-PT-{report_id}",
        "source_record_id": report_id,
        "source": "Clinical_Patient_Intake",
        "source_url": source_url,
        "drug_name": drug_name,
        "evidence_type": "Clinical observation",
        "retrieved_at": retrieved_at,
        "schema_version": "1.0.0",
        "provenance": provenance,
        "data_origin": data_origin,
        "adverse_event": adverse_event,
    }

    # 2. Build SharedEvidenceContract
    contract = from_evidence_record(
        evidence_dict,
        validation_status="VALID",
        duplicate_status="UNIQUE",
        conflict_status="NO_CONFLICT",
        human_review_status="PENDING",
        producer_record={
            "report_id": report_id,
            "pseudonymized_patient_id": pseudonymized_patient,
            "drug_name": drug_name,
            "adverse_event": adverse_event,
            "reporter_role": payload.get("reporter_role", "HEALTHCARE_PROFESSIONAL"),
            "intake_timestamp": retrieved_at,
        },
        notes="Clinical patient observation ingested with sanitized PII. Mandatory human review required.",
    )

    # 3. Validate through live QC Engine
    qc_rec = build_qc_record_from_contract(contract.to_dict())
    qc_result = validate_qc_record(qc_rec)

    # 4. Storage with audit if requested
    stored = False
    if store_evidence and contract.validation_status == "VALID":
        try:
            stored_record = {
                "evidence_id": contract.evidence_id,
                "source_record_id": contract.source_record_id,
                "drug_name": contract.drug_name,
                "adverse_event": contract.adverse_event,
                "source": contract.source,
                "source_url": contract.source_url,
                "evidence_type": contract.evidence_type,
                "retrieved_at": contract.retrieved_at,
                "data_origin": contract.data_origin,
                "provenance": contract.provenance,
                "validation_status": contract.validation_status,
                "human_review_status": contract.human_review_status,
            }
            # Append audit trail via evidence_store
            added_count = add_evidence_with_audit([stored_record])
            stored = added_count > 0
        except Exception as exc:
            log_event("PATIENT_INTAKE_STORAGE_ERROR", error=str(exc))
            stored = False

    return {
        "status": "ACCEPTED",
        "report_id": report_id,
        "pseudonymized_patient_id": pseudonymized_patient,
        "contract": contract.to_dict(),
        "qc_status": qc_result.get("qc_status"),
        "qc_result": qc_result,
        "stored": stored,
        "human_review_required": True,
        "service_disclaimer": (
            "Patient clinical observation has been pseudonymized and ingested for clinical review. "
            "This observation does not establish causal drug toxicity and requires independent clinical review."
        ),
    }


def get_patient_data_status() -> Dict[str, Any]:
    """Return status of the Patient Data & Clinical Intake component."""
    return {
        "available": True,
        "service": "Patient Data & Clinical Intake",
        "version": "1.0.0",
        "pii_protection": "SHA-256 Pseudonymization Active",
        "human_review_enforced": True,
        "status": "AVAILABLE",
        "endpoints": [
            "POST /api/v1/patient/intake",
        ],
    }
