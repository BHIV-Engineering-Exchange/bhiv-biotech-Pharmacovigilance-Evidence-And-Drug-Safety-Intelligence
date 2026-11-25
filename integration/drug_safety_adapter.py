"""
BHIV BiotechSystem — Drug Safety Integration Adapter (Shravani boundary)
Hariom Upadhyay | Backend Architecture & Integration | EOD 20 November 2026

Provides a safe read-only adapter for Shravani's drug safety import pipeline
(repo: bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence,
 branch: drug-safety-evidence-integration, PR #1 — NOT merged into main).

DOCUMENTED BLOCKER:
  All 10 staged producer records currently fail receiver validation because
  source_url and required provenance fields are missing from the input data.
  Shravani's PR is not merged. This adapter reads the staged output from that
  branch and surfaces the validation status accurately.

This adapter:
  - Reads Shravani's staged_receiver_records.json when the branch is locally present.
  - Does NOT copy Shravani's source code into this repository.
  - Does NOT resolve the provenance blocker — it documents it.
  - Preserves invalid records as-is for human review.

STATUS: IMPLEMENTED / UNTESTED — dependent on Shravani PR #1 merge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Service boundary status
# ---------------------------------------------------------------------------

DRUG_SAFETY_BRANCH_AVAILABLE = False
_drug_safety_staged_path: Optional[Path] = None

# Integration work is on the drug-safety-evidence-integration branch.
# After merge, files will be in integration_work/ subdirectory.
_candidate_paths = [
    Path(__file__).resolve().parent.parent / "integration_work" / "staged_receiver_records.json",
    Path(__file__).resolve().parent.parent / "integration_work" / "drug_safety_input.json",
]

for _p in _candidate_paths:
    if _p.exists():
        _drug_safety_staged_path = _p
        DRUG_SAFETY_BRANCH_AVAILABLE = True
        break


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_staged_records() -> Dict[str, Any]:
    """
    Load staged receiver records from Shravani's integration work.

    Returns a structured result with:
      - records: list of staged records (may be empty)
      - failed_validation: list of records that failed receiver validation
      - status: "AVAILABLE" | "NOT_AVAILABLE"
      - blocker: explanation when not available
    """
    staged_path = _drug_safety_staged_path
    if not DRUG_SAFETY_BRANCH_AVAILABLE or staged_path is None:
        return {
            "status": "NOT_AVAILABLE",
            "records": [],
            "failed_validation_count": 0,
            "failed_validation_records": [],
            "blocker": (
                "Shravani's integration_work/ files are not present in this working tree. "
                "They exist on branch drug-safety-evidence-integration (PR #1) which is "
                "not merged into main. "
                "KNOWN BLOCKER: All 10 staged producer records fail receiver validation "
                "because source_url and required provenance fields are missing. "
                "NEXT ACTION: Shravani to fix provenance fields; Hariom to re-run "
                "adapter tests after PR merge."
            ),
            "dependency_pr": (
                "https://github.com/BHIV-Engineering-Exchange/"
                "bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/pull/1"
            ),
        }

    try:
        with open(staged_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "ERROR",
            "records": [],
            "failed_validation_count": 0,
            "failed_validation_records": [],
            "blocker": f"Could not read staged records: {exc}",
        }

    records = data if isinstance(data, list) else data.get("records", [])
    valid_records = []
    invalid_records = []

    for rec in records:
        if not isinstance(rec, dict):
            continue
        # Classify based on the receiver validation status embedded by Shravani's adapter
        rv = rec.get("receiver_validation", {})
        if isinstance(rv, dict) and rv.get("valid") is True:
            valid_records.append(rec)
        else:
            invalid_records.append({
                "record": rec,
                "validation_errors": (
                    rv.get("errors", ["Unknown validation failure"])
                    if isinstance(rv, dict)
                    else ["No receiver_validation field"]
                ),
                "human_review_required": True,
                "disposition": "PRESERVED_FOR_REVIEW",
            })

    return {
        "status": "AVAILABLE",
        "records": valid_records,
        "failed_validation_count": len(invalid_records),
        "failed_validation_records": invalid_records,
        "blocker": (
            f"{len(invalid_records)} records failed receiver validation "
            f"(source_url and provenance fields missing). "
            f"Preserved for human review. Not automatically resolved."
        ) if invalid_records else None,
        "source_file": str(staged_path),
    }


def get_drug_safety_status() -> Dict[str, Any]:
    """Return the current Drug Safety integration status."""
    staged = get_staged_records()
    return {
        "available": DRUG_SAFETY_BRANCH_AVAILABLE,
        "staged_file": str(_drug_safety_staged_path) if _drug_safety_staged_path else None,
        "dependency_repo": (
            "https://github.com/BHIV-Engineering-Exchange/"
            "bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence"
        ),
        "dependency_branch": "drug-safety-evidence-integration",
        "dependency_pr": (
            "https://github.com/BHIV-Engineering-Exchange/"
            "bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/pull/1"
        ),
        "status": "CONNECTED_WITH_KNOWN_BLOCKER" if DRUG_SAFETY_BRANCH_AVAILABLE else "BLOCKED",
        "record_count": len(staged.get("records", [])) + staged.get("failed_validation_count", 0),
        "failed_validation_count": staged.get("failed_validation_count", 0),
        "blocker": staged.get("blocker") or (
            "Shravani PR #1 not merged. 10/10 producer records fail receiver validation "
            "due to missing source_url and provenance fields. "
            "NEXT ACTION: Shravani to fix input data and re-run adapter tests."
        ),
    }


def build_contract_from_drug_safety_record(
    staged_item: Dict[str, Any],
) -> Any:
    """
    Wrap a staged Drug Safety record into a SharedEvidenceContract.
    Preserves all provenance and failure details without fabricating missing data.
    """
    from integration.shared_evidence_contract import (
        SharedEvidenceContract,
        from_evidence_record,
    )

    candidate = staged_item.get("receiver_candidate") if isinstance(staged_item, dict) and "receiver_candidate" in staged_item else staged_item
    if not isinstance(candidate, dict):
        raise TypeError("staged_item must be a dictionary or contain 'receiver_candidate'")

    evidence_id = str(candidate.get("evidence_id") or "EV-UNKNOWN")
    source_record_id = str(candidate.get("source_record_id") or evidence_id)
    drug_name = str(candidate.get("drug_name") or "UNKNOWN_DRUG")
    source_url = str(candidate.get("source_url") or "")

    provenance = candidate.get("provenance") if isinstance(candidate.get("provenance"), dict) else {
        "source_system": candidate.get("source") or "DrugSafetyStaging",
        "underlying_dataset": "staged_receiver_records.json",
    }
    if not provenance.get("source_system"):
        provenance["source_system"] = "DrugSafetyStaging"

    rv = staged_item.get("receiver_validation", {}) if isinstance(staged_item, dict) else {}
    is_valid = bool(rv.get("valid", False))
    qc_errors = rv.get("errors", []) if not is_valid else []

    contract = from_evidence_record(
        {
            "evidence_id": evidence_id,
            "source_record_id": source_record_id,
            "source": candidate.get("source", "DrugSafetyStaging"),
            "source_url": source_url,
            "drug_name": drug_name,
            "evidence_type": "Drug safety biosimilarity record",
            "retrieved_at": candidate.get("retrieved_at", "2026-11-25T10:00:00+00:00"),
            "schema_version": candidate.get("schema_version", "1.1"),
            "provenance": provenance,
            "data_origin": candidate.get("data_origin", "REAL_WORLD"),
            "adverse_event": candidate.get("adverse_event"),
        },
        validation_status="VALID" if is_valid else "INVALID",
        duplicate_status="UNKNOWN",
        conflict_status="UNKNOWN",
        human_review_status="PENDING",
        producer_record=staged_item,
        producer_validation_status="FAILED" if not is_valid else "PASSED",
        qc_errors=qc_errors if qc_errors else None,
        notes="Staged Drug Safety record from Shravani branch. Preserved for review.",
    )
    return contract


def validate_drug_safety_through_qc(staged_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bridge a staged Drug Safety record through Shyamal's QC Engine.
    """
    from integration.qc_adapter import (
        build_qc_record_from_contract,
        validate_qc_record,
    )

    contract = build_contract_from_drug_safety_record(staged_item)
    qc_record = build_qc_record_from_contract(contract.to_dict())
    return validate_qc_record(qc_record)

