"""
BHIV BiotechSystem — QC Engine Adapter
Hariom Upadhyay | Backend Architecture & Integration | EOD 20 November 2026

Provides a safe, documented service-boundary adapter for Shyamal's QC Engine
(repo: bhiv-biotech-symmetrical-octo-invention, branch: feature/runtime-json-schema-validation).

The QC engine is a SEPARATE repository and has NOT been merged into main.
This adapter documents the exact integration boundary:
  - If the QC engine package is installed or importable, it uses the real engine.
  - Otherwise, it returns a SERVICE_BOUNDARY_NOT_MET status with full details.

This adapter NEVER copies the QC engine source code into this repository.
Integration is by import boundary only.

Known QC engine interface (from code inspection):
  qc_engine/engine.py:
    validate_record(record: dict) -> dict
    process_dataset(records: list) -> dict

  schemas/evidence_qc_schema_v1.0.0.json:
    Required fields:
      schema_version, evidence_id, study_id, source, protocol_reference,
      sample_identification, control_identification, experimental_conditions,
      measurement_method, method_validation_status, raw_data_availability,
      missing_data, deviations, statistical_reporting, reproducibility,
      limitations, evidence_category, synthetic_data_declaration,
      reviewer_status, evidence_quality, final_review_status

STATUS: IMPLEMENTED / UNTESTED — QC engine not installed in this environment.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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
# Public interface
# ---------------------------------------------------------------------------

def validate_qc_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a single QC evidence record through Shyamal's QC Engine.

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
        raw_result = _qc_validate_record(record)

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
        raw_result = _qc_process_dataset(records)
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
) -> Dict[str, Any]:
    """
    Map a SharedEvidenceContract dict to the QC engine's expected schema.

    PROPOSED MAPPING — not approved by Shyamal.
    Required QC fields that cannot be derived from the evidence contract
    are explicitly marked as NOT_REPORTED.

    This function documents the exact mapping gap; it does NOT fabricate
    scientific evidence.
    """
    return {
        "schema_version": "1.0.0",
        "evidence_id": contract_dict.get("evidence_id", ""),
        "study_id": contract_dict.get("source_record_id", ""),
        "source": contract_dict.get("source", ""),
        # Fields below require Shyamal's QC schema fields that are not present
        # in the pharmacovigilance evidence contract.
        # Marked NOT_REPORTED — requires cross-team alignment.
        "protocol_reference": "NOT_REPORTED",
        "sample_identification": "NOT_REPORTED",
        "control_identification": "NOT_REPORTED",
        "experimental_conditions": "NOT_REPORTED",
        "measurement_method": "NOT_REPORTED",
        "method_validation_status": "NOT_REPORTED",
        "raw_data_availability": "NOT_REPORTED",
        "missing_data": "NOT_REPORTED",
        "deviations": "NOT_REPORTED",
        "statistical_reporting": "NOT_REPORTED",
        "reproducibility": "NOT_REPORTED",
        "limitations": "NOT_REPORTED",
        "evidence_category": contract_dict.get("evidence_type", "NOT_REPORTED"),
        "synthetic_data_declaration": (
            "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING"
            if contract_dict.get("data_origin") in ("SYNTHETIC", "TEST", "BENCHMARK")
            else "REAL / SOURCE-VERIFIED"
        ),
        "reviewer_status": contract_dict.get("human_review_status", "NOT REVIEWED"),
        "evidence_quality": contract_dict.get("validation_status", "NEEDS REVIEW"),
        "final_review_status": "OPEN",
        "_mapping_note": (
            "PROPOSED_MAPPING — fields marked NOT_REPORTED require "
            "cross-team alignment with Shyamal (QC Engine owner). "
            "Mapping not approved."
        ),
    }


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
