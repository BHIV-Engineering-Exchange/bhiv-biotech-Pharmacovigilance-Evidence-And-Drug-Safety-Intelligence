"""
BHIV BiotechSystem — QC Engine Adapter
Hariom Upadhyay | Backend Architecture & Integration | EOD 20 November 2026
Updated: 24 November 2026 (QC schema v1.0.0 field format and enum alignment)

Provides a safe, documented service-boundary adapter for Shyamal's QC Engine
(repo: bhiv-biotech-symmetrical-octo-invention, branch: feature/runtime-json-schema-validation).

The QC engine is a SEPARATE repository and has NOT been merged into main.
This adapter documents the exact integration boundary:
  - If the QC engine package is installed or importable, it uses the real engine.
  - Otherwise, it returns a SERVICE_BOUNDARY_NOT_MET status with full details.

This adapter NEVER copies the QC engine source code into this repository.
Integration is by import boundary only.

Known QC engine interface (from code inspection of PR #1):
  qc_engine/engine.py:
    validate_record(record: dict) -> dict
    process_dataset(records: list) -> dict

  schemas/evidence_qc_schema_v1.0.0.json (Draft 2020-12, additionalProperties: false):
    21 Required fields:
      schema_version, evidence_id, study_id, source, protocol_reference,
      sample_identification, control_identification, experimental_conditions,
      measurement_method, method_validation_status, raw_data_availability,
      missing_data (array), deviations (array), statistical_reporting,
      reproducibility, limitations, evidence_category (enum),
      synthetic_data_declaration (enum), reviewer_status (enum),
      evidence_quality (enum), final_review_status (enum)

STATUS: IMPLEMENTED / UNTESTED — QC engine package not merged/installed in this environment.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

QC_ENGINE_AVAILABLE = False
_qc_engine_import_error: Optional[str] = None

try:
    # Attempt import from the QC engine package
    # The QC engine must be installed as a package or added to PYTHONPATH.
    # Install command: pip install -e /path/to/bhiv-biotech-symmetrical-octo-invention
    from qc_engine.engine import validate_record as _qc_validate_record  # type: ignore
    from qc_engine.engine import process_dataset as _qc_process_dataset  # type: ignore
    QC_ENGINE_AVAILABLE = True
except ImportError as _e:
    _qc_engine_import_error = str(_e)


# ---------------------------------------------------------------------------
# QC Schema Allowed Enums & Domain Mappings (Draft 2020-12 Spec)
# ---------------------------------------------------------------------------

ALLOWED_QC_CATEGORIES = (
    "Analytical",
    "Structural",
    "Functional",
    "PK",
    "PD",
    "Immunogenicity",
    "Preclinical",
    "Clinical",
)

ALLOWED_QC_QUALITY_VALUES = (
    "VERIFIED",
    "PARTIAL",
    "NEEDS REVIEW",
    "CONFLICTING",
    "INSUFFICIENT",
)

ALLOWED_QC_REVIEWER_STATUSES = (
    "NOT REVIEWED",
    "IN REVIEW",
    "REVIEWED",
    "REQUIRES SECOND REVIEW",
    "CLOSED",
)

ALLOWED_QC_FINAL_REVIEW_STATUSES = (
    "OPEN",
    "IN REVIEW",
    "REQUIRES REVISION",
    "READY FOR HUMAN REVIEW",
    "REVIEWED",
    "CLOSED",
)

ALLOWED_QC_SYNTHETIC_DECLARATIONS = (
    "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING",
    "REAL / SOURCE-VERIFIED",
)

# Deterministic mappings from SharedEvidenceContract fields to QC schema enums:
EVIDENCE_CATEGORY_MAPPING: Dict[str, str] = {
    # Clinical Pharmacovigilance / real-world adverse-event reports
    "FAERS adverse-event report": "Clinical",
    "Clinical observation": "Clinical",
    "Clinical report": "Clinical",
    "Clinical trial adverse event": "Clinical",
    "Clinical": "Clinical",
    # Preclinical / Biosimilarity / Candidate records
    "Drug safety biosimilarity record": "Preclinical",
    "Drug discovery candidate record": "Preclinical",
    "Preclinical study": "Preclinical",
    "Preclinical": "Preclinical",
    # Analytical & Lab Assay categories
    "Analytical": "Analytical",
    "Structural": "Structural",
    "Functional": "Functional",
    "PK": "PK",
    "PD": "PD",
    "Immunogenicity": "Immunogenicity",
}

EVIDENCE_QUALITY_MAPPING: Dict[str, str] = {
    "VALID": "VERIFIED",
    "INVALID": "INSUFFICIENT",
    "REVIEW_REQUIRED": "NEEDS REVIEW",
    "PENDING": "NEEDS REVIEW",
    "PARTIAL": "PARTIAL",
    "CONFLICTING": "CONFLICTING",
    "VERIFIED": "VERIFIED",
    "INSUFFICIENT": "INSUFFICIENT",
    "NEEDS REVIEW": "NEEDS REVIEW",
}

REVIEWER_STATUS_MAPPING: Dict[str, str] = {
    "PENDING": "NOT REVIEWED",
    "NOT_REVIEWED": "NOT REVIEWED",
    "NOT REVIEWED": "NOT REVIEWED",
    "IN_REVIEW": "IN REVIEW",
    "IN REVIEW": "IN REVIEW",
    "REVIEWED": "REVIEWED",
    "REQUIRES_SECOND_REVIEW": "REQUIRES SECOND REVIEW",
    "REQUIRES SECOND REVIEW": "REQUIRES SECOND REVIEW",
    "CLOSED": "CLOSED",
    "NOT_REQUIRED": "NOT REVIEWED",
}


def map_evidence_category(evidence_type: Optional[str]) -> str:
    """
    Map contract evidence_type to QC schema evidence_category enum.

    If category is unmappable or unknown, returns the raw value unchanged so
    that schema validation catches the enum violation without silently fabricating
    a matching domain category.
    """
    if not evidence_type:
        return ""
    if evidence_type in EVIDENCE_CATEGORY_MAPPING:
        return EVIDENCE_CATEGORY_MAPPING[evidence_type]
    if evidence_type in ALLOWED_QC_CATEGORIES:
        return evidence_type
    # Return raw value to let schema validator catch the enum violation safely
    return str(evidence_type)


def map_evidence_quality(
    validation_status: Optional[str],
    conflict_status: Optional[str] = None,
) -> str:
    """
    Map contract validation_status and conflict_status to QC schema evidence_quality enum.

    If conflict_status == "CONFLICT", quality is mapped to "CONFLICTING".
    If validation_status is unknown, returns the raw value unchanged to trigger
    schema validation failure.
    """
    if conflict_status == "CONFLICT":
        return "CONFLICTING"
    if not validation_status:
        return "NEEDS REVIEW"
    if validation_status in EVIDENCE_QUALITY_MAPPING:
        return EVIDENCE_QUALITY_MAPPING[validation_status]
    if validation_status in ALLOWED_QC_QUALITY_VALUES:
        return validation_status
    # Return raw value to let schema validator catch the enum violation safely
    return str(validation_status)


def map_reviewer_status(human_review_status: Optional[str]) -> str:
    """
    Map contract human_review_status to QC schema reviewer_status enum.

    If human_review_status is unknown, returns the raw value unchanged to trigger
    schema validation failure.
    """
    if not human_review_status:
        return "NOT REVIEWED"
    if human_review_status in REVIEWER_STATUS_MAPPING:
        return REVIEWER_STATUS_MAPPING[human_review_status]
    if human_review_status in ALLOWED_QC_REVIEWER_STATUSES:
        return human_review_status
    # Return raw value to let schema validator catch the enum violation safely
    return str(human_review_status)


def map_final_review_status(
    human_review_status: Optional[str],
    validation_status: Optional[str] = None,
) -> str:
    """Map contract review statuses to QC schema final_review_status enum."""
    hrs = (human_review_status or "").upper()
    val = (validation_status or "").upper()
    if hrs in ("REVIEWED",):
        return "REVIEWED"
    if hrs in ("CLOSED",):
        return "CLOSED"
    if hrs in ("IN_REVIEW", "IN REVIEW"):
        return "IN REVIEW"
    if hrs in ("REQUIRES_SECOND_REVIEW", "REQUIRES SECOND REVIEW"):
        return "READY FOR HUMAN REVIEW"
    if hrs in ("PENDING", "NOT_REQUIRED", "") or val in ("REVIEW_REQUIRED", "PENDING"):
        return "READY FOR HUMAN REVIEW"
    return "OPEN"


def map_synthetic_declaration(data_origin: Optional[str], evidence_id: str = "") -> str:
    """Map data_origin and evidence_id to QC schema synthetic_data_declaration enum."""
    orig = (data_origin or "").upper()
    if orig in ("SYNTHETIC", "TEST", "BENCHMARK") or evidence_id.startswith("SYNTH"):
        return "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING"
    return "REAL / SOURCE-VERIFIED"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def validate_qc_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a single QC evidence record through Shyamal's QC Engine.

    Internal keys starting with '_' (such as '_mapping_note') are sanitized
    and stripped before invocation because the schema forbids additionalProperties.

    Returns:
        {
          "qc_status": "PASS" | "FAIL" | "SERVICE_BOUNDARY_NOT_MET",
          "qc_errors": List[str],
          "engine_available": bool,
          "engine_version": str | None,
          "blocker": str | None,  # Present when engine not available
          "raw_result": dict | None,  # Raw engine output when available
        }
    """
    if not QC_ENGINE_AVAILABLE:
        return {
            "qc_status": "SERVICE_BOUNDARY_NOT_MET",
            "qc_errors": [],
            "engine_available": False,
            "engine_version": None,
            "blocker": (
                f"QC Engine (Shyamal) is not installed in this environment. "
                f"Import error: {_qc_engine_import_error}. "
                f"Required: pip install -e bhiv-biotech-symmetrical-octo-invention "
                f"with branch feature/runtime-json-schema-validation checked out. "
                f"Dependent PR: https://github.com/BHIV-Engineering-Exchange/"
                f"bhiv-biotech-symmetrical-octo-invention/pull/1 (not merged)."
            ),
            "raw_result": None,
        }

    try:
        # Strip internal/metadata keys before passing to QC engine
        clean_record = {k: v for k, v in record.items() if not k.startswith("_")}
        raw_result = _qc_validate_record(clean_record)

        # Normalise the QC engine result to our boundary contract
        if isinstance(raw_result, dict):
            passed = raw_result.get("passed", raw_result.get("valid", False))
            errors = raw_result.get("errors", raw_result.get("validation_errors", []))
        else:
            passed = False
            errors = ["Unexpected QC engine response format"]

        return {
            "qc_status": "PASS" if passed else "FAIL",
            "qc_errors": errors if isinstance(errors, list) else [str(errors)],
            "engine_available": True,
            "engine_version": "1.0.0",
            "blocker": None,
            "raw_result": raw_result,
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "qc_status": "FAIL",
            "qc_errors": [f"QC engine raised exception: {exc}"],
            "engine_available": True,
            "engine_version": "1.0.0",
            "blocker": None,
            "raw_result": None,
        }


def validate_qc_dataset(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a list of QC evidence records through Shyamal's QC Engine.

    Returns aggregate results with per-record statuses.
    """
    if not QC_ENGINE_AVAILABLE:
        return {
            "total": len(records),
            "passed": 0,
            "failed": 0,
            "service_boundary_not_met": len(records),
            "engine_available": False,
            "blocker": (
                f"QC Engine not available. {_qc_engine_import_error}"
            ),
            "results": [],
        }

    try:
        clean_records = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
        raw_result = _qc_process_dataset(clean_records)
        return {
            "total": len(records),
            "passed": raw_result.get("passed", 0),
            "failed": raw_result.get("failed", 0),
            "service_boundary_not_met": 0,
            "engine_available": True,
            "blocker": None,
            "results": raw_result.get("results", []),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "total": len(records),
            "passed": 0,
            "failed": len(records),
            "service_boundary_not_met": 0,
            "engine_available": True,
            "blocker": None,
            "error": str(exc),
            "results": [],
        }


def build_qc_record_from_contract(
    contract_dict: Dict[str, Any],
    include_mapping_note: bool = False,
) -> Dict[str, Any]:
    """
    Map a SharedEvidenceContract dict to the QC engine's Draft 2020-12 expected schema.
    (schemas/evidence_qc_schema_v1.0.0.json)

    Deterministic mappings:
      - deviations: array of strings (empty list [] if None or 'NOT_REPORTED')
      - missing_data: array of strings (empty list [] if None or 'NOT_REPORTED')
      - evidence_category: mapped to schema enum via EVIDENCE_CATEGORY_MAPPING
      - evidence_quality: mapped to schema enum via map_evidence_quality
      - reviewer_status: mapped to schema enum via map_reviewer_status
      - final_review_status: mapped to schema enum via map_final_review_status
      - synthetic_data_declaration: mapped to allowed schema enum
      - Internal metadata keys (such as _mapping_note) are omitted by default
        so that strict schema validation (additionalProperties: false) succeeds.
      - Original contract_dict is never mutated.

    Required QC fields not present in the pharmacovigilance evidence contract
    are explicitly marked as 'NOT_REPORTED' (strings of length >= 1) to document
    the boundary gap without fabricating scientific evidence.
    """
    # Safe read of contract dict without in-place mutation
    evidence_id = str(contract_dict.get("evidence_id") or "")
    study_id = str(contract_dict.get("source_record_id") or contract_dict.get("study_id") or "")
    source = str(contract_dict.get("source") or "")

    # Deviations: must be a JSON array of strings
    deviations_val = contract_dict.get("deviations")
    if isinstance(deviations_val, list):
        qc_deviations = [str(d) for d in deviations_val]
    elif isinstance(deviations_val, str) and deviations_val != "NOT_REPORTED":
        qc_deviations = [deviations_val]
    else:
        qc_deviations = []

    # Missing data: must be a JSON array of strings
    missing_val = contract_dict.get("missing_data")
    if isinstance(missing_val, list):
        qc_missing = [str(m) for m in missing_val]
    elif isinstance(missing_val, str) and missing_val != "NOT_REPORTED":
        qc_missing = [missing_val]
    else:
        qc_missing = []

    # Map enums deterministically
    evidence_cat = map_evidence_category(
        contract_dict.get("evidence_type") or contract_dict.get("evidence_category")
    )
    evidence_qual = map_evidence_quality(
        contract_dict.get("validation_status") or contract_dict.get("evidence_quality"),
        contract_dict.get("conflict_status"),
    )
    rev_status = map_reviewer_status(
        contract_dict.get("human_review_status") or contract_dict.get("reviewer_status")
    )
    final_rev = map_final_review_status(
        contract_dict.get("human_review_status") or contract_dict.get("reviewer_status"),
        contract_dict.get("validation_status"),
    )
    synth_decl = map_synthetic_declaration(
        contract_dict.get("data_origin"),
        evidence_id=evidence_id,
    )

    qc_record: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "evidence_id": evidence_id,
        "study_id": study_id,
        "source": source,
        "protocol_reference": str(contract_dict.get("protocol_reference") or "NOT_REPORTED"),
        "sample_identification": str(contract_dict.get("sample_identification") or "NOT_REPORTED"),
        "control_identification": str(contract_dict.get("control_identification") or "NOT_REPORTED"),
        "experimental_conditions": str(contract_dict.get("experimental_conditions") or "NOT_REPORTED"),
        "measurement_method": str(contract_dict.get("measurement_method") or "NOT_REPORTED"),
        "method_validation_status": str(contract_dict.get("method_validation_status") or "NOT_REPORTED"),
        "raw_data_availability": str(contract_dict.get("raw_data_availability") or "NOT_REPORTED"),
        "missing_data": qc_missing,
        "deviations": qc_deviations,
        "statistical_reporting": str(contract_dict.get("statistical_reporting") or "NOT_REPORTED"),
        "reproducibility": str(contract_dict.get("reproducibility") or "NOT_REPORTED"),
        "limitations": str(contract_dict.get("limitations") or "NOT_REPORTED"),
        "evidence_category": evidence_cat,
        "synthetic_data_declaration": synth_decl,
        "reviewer_status": rev_status,
        "evidence_quality": evidence_qual,
        "final_review_status": final_rev,
    }

    if include_mapping_note:
        qc_record["_mapping_note"] = (
            "PROPOSED_MAPPING — fields marked NOT_REPORTED indicate preclinical "
            "assay parameters not present in clinical pharmacovigilance reports. "
            "All enums mapped deterministically."
        )

    return qc_record


def validate_qc_schema_direct(
    record: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Direct schema validation against Draft 2020-12 QC schema.

    Enables local and unit-test validation even when Shyamal's QC Engine
    package is not installed.
    """
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return {
            "valid": False,
            "errors": ["jsonschema package is required for direct schema validation"],
        }

    clean_record = {k: v for k, v in record.items() if not k.startswith("_")}

    if schema is None:
        schema = get_qc_schema_definition()

    if not schema:
        return {
            "valid": False,
            "errors": ["QC schema definition could not be located"],
        }

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for e in validator.iter_errors(clean_record):
        field_path = "/".join(str(p) for p in e.path)
        if field_path:
            errors.append(f"{field_path}: {e.message}")
        else:
            errors.append(e.message)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def get_qc_schema_definition() -> Optional[Dict[str, Any]]:
    """Locate and load the canonical QC JSON schema v1.0.0."""
    candidate_paths = [
        Path(__file__).resolve().parent.parent / "schemas" / "evidence_qc_schema_v1.0.0.json",
        Path("C:/Users/Microsoft/.gemini/antigravity/scratch/bhiv-qc-fresh/schemas/evidence_qc_schema_v1.0.0.json"),
        Path(__file__).resolve().parent.parent.parent / "bhiv-qc-fresh" / "schemas" / "evidence_qc_schema_v1.0.0.json",
        Path(__file__).resolve().parent.parent.parent / "bhiv-biotech-symmetrical-octo-invention" / "schemas" / "evidence_qc_schema_v1.0.0.json",
    ]

    for path in candidate_paths:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    return None


def get_qc_engine_status() -> Dict[str, Any]:
    """Return the current QC engine availability status."""
    return {
        "available": QC_ENGINE_AVAILABLE,
        "import_error": _qc_engine_import_error,
        "dependency_repo": (
            "https://github.com/BHIV-Engineering-Exchange/"
            "bhiv-biotech-symmetrical-octo-invention"
        ),
        "dependency_branch": "feature/runtime-json-schema-validation",
        "dependency_pr": (
            "https://github.com/BHIV-Engineering-Exchange/"
            "bhiv-biotech-symmetrical-octo-invention/pull/1"
        ),
        "status": "IMPLEMENTED / UNTESTED" if not QC_ENGINE_AVAILABLE else "VERIFIED",
        "blocker": (
            "QC engine PR not merged; not installed as package. "
            "NEXT ACTION: Shyamal to publish package or merge PR. "
            "Hariom to run integration tests once available."
        ) if not QC_ENGINE_AVAILABLE else None,
    }
