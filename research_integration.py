"""Small source-linked research workflow for the existing pharmacovigilance pipeline."""

import copy
from typing import Callable, Dict, Any

from src.openfda_connector import search_drug
from src.normalize_evidence import normalize_record
from src.evidence_schema import validate_evidence


def validate_research_report(report: Any) -> Dict[str, Any]:
    """Validate the smallest report contract without altering the original data."""
    if not isinstance(report, dict):
        return {"valid": False, "errors": ["Report must be a dictionary"]}

    errors = []
    report_id = report.get("report_id")
    drug_name = report.get("drug_name")

    if not isinstance(report_id, str) or not report_id.strip():
        errors.append("Missing report_id")
    if not isinstance(drug_name, str) or not drug_name.strip():
        errors.append("Missing drug_name")

    return {"valid": not errors, "errors": errors}


def run_research_workflow(
    report: Any,
    limit: int = 5,
    retriever: Callable = search_drug,
) -> Dict[str, Any]:
    """
    Retrieve and normalize source-linked evidence for human review.

    This workflow does not diagnose, prescribe, rank clinical recommendations,
    or establish causality. OpenFDA/FAERS reports are source-derived associations
    requiring independent clinical review.
    """
    validation = validate_research_report(report)
    original_report = copy.deepcopy(report) if isinstance(report, dict) else copy.deepcopy(report)

    if not validation["valid"]:
        return {
            "status": "INVALID_INPUT",
            "original_report": original_report,
            "normalized_input": None,
            "findings": [],
            "uncertainty": {
                "level": "HIGH",
                "limitations": validation["errors"],
                "missing_evidence": "A valid report_id and drug_name are required.",
            },
            "human_review": {
                "required": True,
                "status": "PENDING",
                "role": "researcher or clinician",
            },
        }

    drug_name = report["drug_name"].strip()
    result = retriever(drug_name, limit=limit)

    normalized_input = {
        "report_id": report["report_id"].strip(),
        "drug_name": drug_name,
        "drug_name_original": report["drug_name"],
    }

    if not isinstance(result, dict):
        return _service_failure(original_report, normalized_input, "Unexpected retriever response.")

    if not result.get("success"):
        return _service_failure(
            original_report,
            normalized_input,
            str(result.get("error") or "Evidence source request failed."),
        )

    if not isinstance(result.get("raw_response"), dict):
        return _service_failure(original_report, normalized_input, "Unexpected source response format.")

    raw_results = result["raw_response"].get("results", [])
    if not isinstance(raw_results, list):
        return _service_failure(original_report, normalized_input, "Unexpected source results format.")

    findings = []
    invalid_count = 0
    for index, raw_record in enumerate(raw_results, start=1):
        if not isinstance(raw_record, dict):
            invalid_count += 1
            continue

        evidence = normalize_record(
            raw_record,
            index,
            result.get("retrieved_at"),
            result.get("source_url"),
            requested_drug_name=drug_name,
        )
        valid, validation_errors = validate_evidence(evidence)
        if not valid:
            invalid_count += 1
            continue

        findings.append({
            "finding": evidence.to_dict(),
            "source": {
                "title": "OpenFDA drug adverse-event report",
                "publisher": "U.S. Food and Drug Administration",
                "database": "FAERS",
                "identifier": evidence.source_record_id,
                "url": evidence.source_url,
                "retrieved_at": evidence.retrieved_at,
            },
            "evidence_origin": "SOURCE_DERIVED",
            "model_generated_summary": False,
        })

    missing_evidence = "No matching source records were returned." if not findings else None
    if invalid_count:
        missing_evidence = (
            f"{invalid_count} source record(s) could not be normalized or validated."
        )

    uncertainty = {
        "level": "HIGH" if not findings else "MEDIUM",
        "limitations": [
            "FAERS records are spontaneous reports and do not establish causality.",
            "Absence of a record does not establish absence of risk.",
            "Entity resolution and data completeness may be incomplete.",
        ],
        "missing_evidence": missing_evidence,
    }

    return {
        "status": "REVIEW_REQUIRED" if findings else "NO_EVIDENCE",
        "original_report": original_report,
        "normalized_input": normalized_input,
        "findings": findings,
        "uncertainty": uncertainty,
        "human_review": {
            "required": True,
            "status": "PENDING",
            "role": "researcher or clinician",
        },
    }


def _service_failure(original_report, normalized_input, reason):
    return {
        "status": "SOURCE_UNAVAILABLE",
        "original_report": original_report,
        "normalized_input": normalized_input,
        "findings": [],
        "uncertainty": {
            "level": "HIGH",
            "limitations": ["Evidence could not be retrieved or normalized."],
            "missing_evidence": reason,
        },
        "human_review": {
            "required": True,
            "status": "PENDING",
            "role": "researcher or clinician",
        },
    }
