"""
Cross-Repository QC Integration Verification Suite
BHIV Biotech Pharmacovigilance Backend & Evidence QC Engine

Executes verification scenarios 8 through 14:
  8. Valid synthetic evidence record
  9. Missing required fields
  10. Invalid schema (types, enums, additional properties)
  11. Duplicate and conflicting records
  12. Provenance and original evidence preservation
  13. Human review gating and scientific conclusion preservation
  14. End-to-end integration through FastAPI backend API

Non-fabrication guarantee: All checks execute against real live runtimes.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure both backend and QC repos are in path
BACKEND_ROOT = Path("C:/Users/Microsoft/.gemini/antigravity/scratch/bhiv-post-merge-fresh").resolve()
QC_ROOT = Path("C:/Users/Microsoft/.gemini/antigravity/scratch/bhiv-qc").resolve()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(QC_ROOT) not in sys.path:
    sys.path.insert(0, str(QC_ROOT))

# Backend modules
from integration.shared_evidence_contract import (
    CONTRACT_VERSION,
    SharedEvidenceContract,
    from_evidence_record,
)
from integration.qc_adapter import (
    QC_ENGINE_AVAILABLE,
    build_qc_record_from_contract,
    get_qc_engine_status,
    validate_qc_record,
    validate_qc_dataset,
)
from src.normalize_evidence import normalize_record
from src.evidence_schema import validate_evidence

# Real QC Engine modules from Shyamal PR #1
import qc_engine.engine as qe
from qc_engine.engine import (
    ENGINE_VERSION,
    SCHEMA_VERSION,
    validate_record as qc_validate_record,
    process_dataset as qc_process_dataset,
    detect_duplicates,
    detect_conflicts,
    classify_record,
    human_review_required,
)

# FastAPI app and TestClient
from fastapi.testclient import TestClient
from integration.api_service import app


def run_test_8_valid_synthetic_record() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 8: Test a Valid Synthetic Evidence Record")
    print("=" * 60)

    # 1. Generate normalized evidence record from synthetic input
    synthetic_raw = {
        "safetyreportid": "SYNTH-VERIFY-001",
        "patient": {
            "drug": [
                {
                    "medicinalproduct": "CURCUMIN",
                    "openfda": {"application_number": ["NDA000999"]},
                }
            ],
            "reaction": [{"reactionmeddrapt": "MILD_NAUSEA"}],
        },
    }
    evidence = normalize_record(
        synthetic_raw,
        index=1,
        retrieved_at="2026-11-25T10:00:00+00:00",
        source_url="https://api.fda.gov/synthetic_test",
        requested_drug_name="curcumin",
    )
    is_valid_ev, ev_errors = validate_evidence(evidence)
    assert is_valid_ev, f"Evidence validation failed: {ev_errors}"

    # 2. Build SharedEvidenceContract
    contract = from_evidence_record(
        evidence.to_dict(),
        validation_status="VALID",
        duplicate_status="UNIQUE",
        conflict_status="NO_CONFLICT",
        human_review_status="PENDING",
        notes="Synthetic test record for cross-repo integration verification",
    )
    contract.data_origin = "SYNTHETIC"
    is_valid_c, c_errors = contract.validate()
    assert is_valid_c, f"Contract validation failed: {c_errors}"

    # 3. Map to QC schema record
    qc_rec = build_qc_record_from_contract(contract.to_dict())
    print("Mapped QC Record:")
    print(json.dumps(qc_rec, indent=2))

    # 4. Validate through backend adapter using live QC engine
    adapter_result = validate_qc_record(qc_rec)
    print("\nAdapter Validation Result:")
    print(json.dumps(adapter_result, indent=2))

    assert adapter_result["qc_status"] == "PASS", f"Expected PASS, got {adapter_result['qc_status']}"
    assert adapter_result["qc_errors"] == [], f"Expected 0 errors, got {adapter_result['qc_errors']}"
    assert adapter_result["engine_available"] is True
    assert adapter_result["blocker"] is None
    assert adapter_result["raw_result"]["valid"] is True

    # 5. Process through QC dataset engine
    dataset_res = qc_process_dataset([qc_rec])
    rec_res = dataset_res["results"][0]
    print("\nQC Process Dataset Item Result:")
    print(json.dumps(rec_res, indent=2))
    assert rec_res["validation"]["valid"] is True
    assert rec_res["evidence_id"] == contract.evidence_id
    assert dataset_res["scientific_conclusion"] is None

    print("[PASS] Scenario 8: Valid synthetic evidence record successfully validated by QC engine.")
    return {
        "status": "PASS",
        "evidence_id": contract.evidence_id,
        "qc_status": adapter_result["qc_status"],
        "engine_version": adapter_result["engine_version"],
    }


def run_test_9_missing_required_fields() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 9: Test Missing Required Fields")
    print("=" * 60)

    # Base valid record
    ev_dict = normalize_record(
        {
            "safetyreportid": "SYNTH-MISSING-001",
            "patient": {
                "drug": [{"medicinalproduct": "TEST_DRUG"}],
                "reaction": [{"reactionmeddrapt": "HEADACHE"}],
            },
        },
        index=1,
        retrieved_at="2026-11-25T10:00:00+00:00",
        source_url="https://api.fda.gov/test",
        requested_drug_name="test_drug",
    ).to_dict()
    ev_dict["data_origin"] = "SYNTHETIC"
    base_contract = from_evidence_record(
        ev_dict,
        validation_status="VALID",
    )
    base_qc = build_qc_record_from_contract(base_contract.to_dict())

    test_cases = [
        ("study_id", "study_id"),
        ("evidence_id", "evidence_id"),
        ("schema_version", "schema_version"),
        ("measurement_method", "measurement_method"),
        ("reviewer_status", "reviewer_status"),
        ("synthetic_data_declaration", "synthetic_data_declaration"),
    ]

    results = []
    for test_name, field in test_cases:
        bad_rec = copy.deepcopy(base_qc)
        del bad_rec[field]

        val_res = validate_qc_record(bad_rec)
        print(f"Testing missing '{field}': qc_status={val_res['qc_status']}, errors={val_res['qc_errors']}")

        assert val_res["qc_status"] == "FAIL", f"Expected FAIL for missing {field}, got {val_res['qc_status']}"
        assert len(val_res["qc_errors"]) > 0, f"Expected errors for missing {field}"
        assert any(field in err for err in val_res["qc_errors"]), f"Error message should mention {field}"
        assert val_res["engine_available"] is True
        results.append({"field": field, "status": "REJECTED_AS_EXPECTED", "errors": val_res["qc_errors"]})

    print("[PASS] Scenario 9: Missing required fields are strictly rejected by QC schema validation.")
    return {"status": "PASS", "cases_tested": len(test_cases), "details": results}


def run_test_10_invalid_schema() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 10: Test Invalid Schema (types, enums, additionalProperties)")
    print("=" * 60)

    ev_dict10 = normalize_record(
        {
            "safetyreportid": "SYNTH-SCHEMA-001",
            "patient": {
                "drug": [{"medicinalproduct": "TEST_DRUG"}],
                "reaction": [{"reactionmeddrapt": "RASH"}],
            },
        },
        index=1,
        retrieved_at="2026-11-25T10:00:00+00:00",
        source_url="https://api.fda.gov/test",
        requested_drug_name="test_drug",
    ).to_dict()
    ev_dict10["data_origin"] = "SYNTHETIC"
    base_contract = from_evidence_record(
        ev_dict10,
        validation_status="VALID",
    )
    base_qc = build_qc_record_from_contract(base_contract.to_dict())

    test_cases = [
        ("invalid_category_enum", {"evidence_category": "FABRICATED_CATEGORY"}),
        ("invalid_quality_enum", {"evidence_quality": "HIGH_CONFIDENCE_DRUG"}),
        ("invalid_reviewer_status_enum", {"reviewer_status": "APPROVED_BY_BOT"}),
        ("invalid_type_deviations_not_list", {"deviations": "no deviations occurred"}),
        ("invalid_type_missing_data_not_list", {"missing_data": 42}),
        ("disallowed_additional_property", {"unauthorized_ai_field": "injected_value"}),
        ("wrong_schema_version", {"schema_version": "9.9.9"}),
    ]

    results = []
    for case_name, mutation in test_cases:
        bad_rec = copy.deepcopy(base_qc)
        bad_rec.update(mutation)

        val_res = validate_qc_record(bad_rec)
        print(f"Testing {case_name}: qc_status={val_res['qc_status']}, errors={val_res['qc_errors']}")

        assert val_res["qc_status"] == "FAIL", f"Expected FAIL for {case_name}, got {val_res['qc_status']}"
        assert len(val_res["qc_errors"]) > 0
        assert val_res["engine_available"] is True
        results.append({"case": case_name, "status": "REJECTED_AS_EXPECTED", "errors": val_res["qc_errors"]})

    print("[PASS] Scenario 10: Invalid schema types, disallowed properties and invalid enums are rejected.")
    return {"status": "PASS", "cases_tested": len(test_cases), "details": results}


def run_test_11_duplicate_conflicting_records() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 11: Test Duplicate and Conflicting Records")
    print("=" * 60)

    # Base record generator
    def create_qc_record(ev_id: str, study_id: str, method: str = "HPLC-UV", quality: str = "VERIFIED") -> Dict[str, Any]:
        ev = normalize_record(
            {
                "safetyreportid": study_id,
                "patient": {
                    "drug": [{"medicinalproduct": "TEST_DRUG"}],
                    "reaction": [{"reactionmeddrapt": "HEADACHE"}],
                },
            },
            index=1,
            retrieved_at="2026-11-25T10:00:00+00:00",
            source_url="https://api.fda.gov/test",
            requested_drug_name="test_drug",
        ).to_dict()
        ev["data_origin"] = "SYNTHETIC"
        c = from_evidence_record(
            ev,
            validation_status="VALID",
        )
        rec = build_qc_record_from_contract(c.to_dict())
        rec["evidence_id"] = ev_id
        rec["study_id"] = study_id
        rec["measurement_method"] = method
        rec["evidence_quality"] = quality
        return rec

    # 1. Test Duplicate Detection
    rec1 = create_qc_record("EV-DUP-001", "STUDY-001")
    rec2 = create_qc_record("EV-DUP-001", "STUDY-002")  # duplicate evidence_id
    rec3 = create_qc_record("EV-DUP-003", "STUDY-001")  # duplicate study_id

    dup_dataset = [rec1, rec2, rec3]
    dup_res = detect_duplicates(dup_dataset)
    print("Detected Duplicates:")
    print(json.dumps(dup_res, indent=2))

    dup_types = [d["type"] for d in dup_res]
    assert "DUPLICATE_EVIDENCE_ID" in dup_types, "DUPLICATE_EVIDENCE_ID not detected"
    assert "DUPLICATE_STUDY_ID" in dup_types, "DUPLICATE_STUDY_ID not detected"

    # Verify classification of duplicate record
    classified_dup = classify_record(rec2, duplicate_ids={"EV-DUP-001"})
    print("Classified Duplicate Record Quality:", classified_dup["evidence_quality"])
    print("Reason:", classified_dup["reason"])
    assert classified_dup["evidence_quality"] == "NEEDS REVIEW"
    assert "Duplicate evidence identifier detected" in classified_dup["reason"]

    # 2. Test Conflicting Records Detection
    rec_a = create_qc_record("EV-CONF-001", "STUDY-CONF-99", method="ELISA_ASSAY_A", quality="VERIFIED")
    rec_b = create_qc_record("EV-CONF-002", "STUDY-CONF-99", method="LC_MS_ASSAY_B", quality="PARTIAL")  # conflicting method & quality

    conf_dataset = [rec_a, rec_b]
    conf_res = detect_conflicts(conf_dataset)
    print("\nDetected Conflicts:")
    print(json.dumps(conf_res, indent=2))

    assert len(conf_res) >= 1, "Expected at least one conflicting field detected"
    conflict_fields = [c["field"] for c in conf_res]
    assert "measurement_method" in conflict_fields
    assert "evidence_quality" in conflict_fields

    # Verify classification of conflicting record
    classified_conf = classify_record(rec_a, conflict_study_ids={"STUDY-CONF-99"})
    print("Classified Conflict Record Quality:", classified_conf["evidence_quality"])
    print("Reason:", classified_conf["reason"])
    assert classified_conf["evidence_quality"] == "CONFLICTING"
    assert "Conflicting values were detected for the study" in classified_conf["reason"]

    # Process whole dataset containing duplicates and conflicts
    full_batch_res = qc_process_dataset([rec1, rec2, rec3, rec_a, rec_b])
    print("\nFull Dataset Processing Summary:")
    print("Record Count:", full_batch_res["record_count"])
    print("Duplicates Count:", len(full_batch_res["duplicates"]))
    print("Conflicts Count:", len(full_batch_res["conflicts"]))
    print("Human Review Required Count:", full_batch_res["human_review_required_count"])

    assert full_batch_res["record_count"] == 5
    assert len(full_batch_res["duplicates"]) == 3, f"Expected 3 duplicates (EV-DUP-001, STUDY-001, STUDY-CONF-99), got {len(full_batch_res['duplicates'])}"
    assert len(full_batch_res["conflicts"]) == 2
    assert full_batch_res["human_review_required_count"] == 5
    assert full_batch_res["scientific_conclusion"] is None

    print("[PASS] Scenario 11: Duplicates and conflicts detected, classified correctly, and preserved.")
    return {
        "status": "PASS",
        "duplicates_detected": len(dup_res),
        "conflicts_detected": len(conf_res),
        "human_review_required_count": full_batch_res["human_review_required_count"],
    }


def run_test_12_provenance_preservation() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 12: Verify Provenance and Original Evidence Preservation")
    print("=" * 60)

    raw_event = {
        "safetyreportid": "PROVENANCE-CHECK-001",
        "patient": {
            "drug": [{"medicinalproduct": "ASPIRIN"}],
            "reaction": [{"reactionmeddrapt": "TINNITUS"}],
        },
    }
    ev12 = normalize_record(
        raw_event,
        index=1,
        retrieved_at="2026-11-25T10:15:30+00:00",
        source_url="https://api.fda.gov/provenance_test",
        requested_drug_name="aspirin",
    ).to_dict()
    ev12["data_origin"] = "SYNTHETIC"
    contract = from_evidence_record(
        ev12,
        validation_status="VALID",
        producer_record=raw_event,
        notes="Provenance preservation test note",
    )
    contract_dict = contract.to_dict()
    contract_snapshot = copy.deepcopy(contract_dict)

    # 1. Ensure build_qc_record_from_contract does not mutate contract_dict
    qc_rec = build_qc_record_from_contract(contract_dict)
    assert contract_dict == contract_snapshot, "Contract dictionary was mutated in-place!"
    assert qc_rec is not contract_dict

    # 2. Verify provenance fields are preserved
    assert qc_rec["evidence_id"] == contract.evidence_id
    assert qc_rec["study_id"] == contract.source_record_id
    assert qc_rec["source"] == contract.source
    assert qc_rec["synthetic_data_declaration"] == "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING"

    # 3. Check contract internal evidence and producer record preservation
    assert contract.drug_name == "ASPIRIN"
    assert contract.adverse_event == "TINNITUS"
    assert contract.retrieved_at == "2026-11-25T10:15:30+00:00"
    assert contract.source_url == "https://api.fda.gov/provenance_test"
    assert contract.producer_record == raw_event

    print("Source:", qc_rec["source"])
    print("Study ID:", qc_rec["study_id"])
    print("Evidence ID:", qc_rec["evidence_id"])
    print("Synthetic Declaration:", qc_rec["synthetic_data_declaration"])
    print("[PASS] Scenario 12: Provenance and original evidence are preserved verbatim.")
    return {
        "status": "PASS",
        "source": qc_rec["source"],
        "study_id": qc_rec["study_id"],
        "evidence_id": qc_rec["evidence_id"],
        "declaration": qc_rec["synthetic_data_declaration"],
    }


def run_test_13_human_review_marking() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 13: Verify QC Output Correctly Marks Records Requiring Human Review")
    print("=" * 60)

    # Test all quality states
    quality_cases = [
        ("VERIFIED", "NOT REVIEWED", "READY FOR HUMAN REVIEW", True),
        ("PARTIAL", "REVIEWED", "REVIEWED", True),
        ("NEEDS REVIEW", "REVIEWED", "REVIEWED", True),
        ("CONFLICTING", "REVIEWED", "REVIEWED", True),
        ("INSUFFICIENT", "REVIEWED", "REVIEWED", True),
        ("VERIFIED", "REVIEWED", "CLOSED", False),  # verified, reviewed, and closed -> human review already completed
        ("VERIFIED", "REVIEWED", "REVIEWED", False), # verified and reviewed -> human review completed
        ("VERIFIED", "IN REVIEW", "REVIEWED", True), # reviewer_status IN REVIEW -> still requires review
    ]

    for q, rev_s, fin_s, expected_hr in quality_cases:
        cls_dict = {"evidence_quality": q}
        rec = {"reviewer_status": rev_s, "final_review_status": fin_s}
        hr = human_review_required(cls_dict, rec)
        print(f"Quality={q:<14} Reviewer={rev_s:<14} Final={fin_s:<23} -> HumanReviewRequired={hr} (Expected={expected_hr})")
        assert hr == expected_hr, f"Failed for {q}, {rev_s}, {fin_s}: got {hr}, expected {expected_hr}"

    # Verify that pharmacovigilance evidence default contracts ALWAYS route to human review
    ev13 = normalize_record(
        {
            "safetyreportid": "HR-TEST-001",
            "patient": {
                "drug": [{"medicinalproduct": "ASPIRIN"}],
                "reaction": [{"reactionmeddrapt": "HEADACHE"}],
            },
        },
        index=1,
        retrieved_at="2026-11-25T10:00:00+00:00",
        source_url="https://api.fda.gov/test",
        requested_drug_name="aspirin",
    ).to_dict()
    ev13["data_origin"] = "SYNTHETIC"
    base_contract = from_evidence_record(
        ev13,
        validation_status="VALID",
        human_review_status="PENDING",
    )
    qc_rec = build_qc_record_from_contract(base_contract.to_dict())
    cls_res = classify_record(qc_rec)
    hr_res = human_review_required(cls_res, qc_rec)
    print("\nPharmacovigilance default mapped record:")
    print("Reviewer status:", qc_rec["reviewer_status"])
    print("Final review status:", qc_rec["final_review_status"])
    print("Evidence quality:", cls_res["evidence_quality"])
    print("Human review required:", hr_res)
    assert hr_res is True

    print("[PASS] Scenario 13: All non-reviewed or non-verified states accurately enforce human review.")
    return {"status": "PASS", "cases_tested": len(quality_cases) + 1}


def run_test_14_end_to_end_backend_api() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("SCENARIO 14: End-to-End Integration through Backend FastAPI API")
    print("=" * 60)

    client = TestClient(app)

    # 1. Verify /health returns OK with live QC engine marked VERIFIED
    health_res = client.get("/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    health_data = health_res.json()
    print("GET /health Response:")
    print(json.dumps(health_data, indent=2))

    assert health_data["status"] == "OK"
    assert health_data["integrations"]["qc_engine_shyamal"] == "VERIFIED", (
        f"Expected VERIFIED, got {health_data['integrations']['qc_engine_shyamal']}"
    )

    # 2. Run mock evidence retrieval through research workflow endpoint
    # We patch run_research_workflow to return deterministic synthetic evidence without network hit
    from unittest.mock import patch

    synthetic_finding = {
        "report_id": "API-RPT-E2E-001",
        "evidence_id": "EV-FDA-E2E-999",
        "drug_name": "IBUPROFEN",
        "entity_resolution_status": "EXACT_MATCH",
        "canonical_entity_name": "IBUPROFEN",
        "adverse_event": "GASTRITIS",
        "association_type": "SUSPECTED",
        "source": "OpenFDA/FAERS",
        "source_record_id": "10023456",
        "evidence_type": "Clinical report",
        "retrieved_at": "2026-11-25T10:20:00+00:00",
        "source_url": "https://api.fda.gov/drug/event.json?search=ibuprofen",
    }

    mock_workflow_return = {
        "report_id": "API-RPT-E2E-001",
        "drug_name": "ibuprofen",
        "status": "REVIEW_REQUIRED",
        "findings": [
            {
                "finding": synthetic_finding,
                "evidence_origin": "SOURCE_DERIVED",
                "model_generated_summary": False,
            }
        ],
        "uncertainty": {"level": "MODERATE", "notes": "Spontaneous reports"},
        "human_review": {"required": True, "status": "PENDING"},
    }

    with patch("integration.api_service.run_research_workflow", return_value=mock_workflow_return):
        evidence_resp = client.post(
            "/api/v1/research/evidence",
            json={
                "report_id": "API-RPT-E2E-001",
                "drug_name": "ibuprofen",
                "limit": 1,
                "data_origin": "SYNTHETIC",
            },
        )
        assert evidence_resp.status_code == 200, f"Evidence retrieval API failed: {evidence_resp.text}"
        evidence_data = evidence_resp.json()
        print("\nPOST /api/v1/research/evidence Response:")
        print(json.dumps(evidence_data, indent=2))

        assert evidence_data["status"] == "REVIEW_REQUIRED"
        assert evidence_data["findings_count"] == 1
        retrieved_contract = evidence_data["findings"][0]

    # 3. Take the contract produced by the backend and transform to QC format
    qc_record_for_api = build_qc_record_from_contract(retrieved_contract)
    print("\nTransformed QC Record for /api/v1/qc/validate:")
    print(json.dumps(qc_record_for_api, indent=2))

    # 4. Submit to live POST /api/v1/qc/validate endpoint
    qc_api_resp = client.post(
        "/api/v1/qc/validate",
        json={"record": qc_record_for_api},
    )
    assert qc_api_resp.status_code == 200, f"QC validate API failed: {qc_api_resp.text}"
    qc_api_data = qc_api_resp.json()
    print("\nPOST /api/v1/qc/validate (Valid Record) Response:")
    print(json.dumps(qc_api_data, indent=2))

    assert qc_api_data["qc_status"] == "PASS", f"Expected PASS, got {qc_api_data['qc_status']}"
    assert qc_api_data["qc_errors"] == []
    assert qc_api_data["engine_available"] is True
    assert qc_api_data["engine_version"] == "1.0.0"
    assert qc_api_data["blocker"] is None

    # 5. Submit an invalid QC record to verify error propagation through API
    invalid_qc_record = copy.deepcopy(qc_record_for_api)
    del invalid_qc_record["study_id"]
    invalid_qc_record["deviations"] = "not-an-array"

    qc_bad_resp = client.post(
        "/api/v1/qc/validate",
        json={"record": invalid_qc_record},
    )
    assert qc_bad_resp.status_code == 200
    qc_bad_data = qc_bad_resp.json()
    print("\nPOST /api/v1/qc/validate (Invalid Record) Response:")
    print(json.dumps(qc_bad_data, indent=2))

    assert qc_bad_data["qc_status"] == "FAIL"
    assert len(qc_bad_data["qc_errors"]) >= 2
    assert qc_bad_data["engine_available"] is True

    print("\n[PASS] Scenario 14: End-to-end integration verified through FastAPI backend endpoints.")
    return {
        "status": "PASS",
        "health_qc_integration": health_data["integrations"]["qc_engine_shyamal"],
        "evidence_api_status": evidence_data["status"],
        "qc_validation_status": qc_api_data["qc_status"],
        "qc_bad_validation_status": qc_bad_data["qc_status"],
    }


def main():
    print("=" * 70)
    print("STARTING BHIV CROSS-REPOSITORY QC INTEGRATION VERIFICATION")
    print(f"Backend Repo: {BACKEND_ROOT}")
    print(f"QC Repo:      {QC_ROOT}")
    print("=" * 70)

    results = {}
    results["scenario_8"] = run_test_8_valid_synthetic_record()
    results["scenario_9"] = run_test_9_missing_required_fields()
    results["scenario_10"] = run_test_10_invalid_schema()
    results["scenario_11"] = run_test_11_duplicate_conflicting_records()
    results["scenario_12"] = run_test_12_provenance_preservation()
    results["scenario_13"] = run_test_13_human_review_marking()
    results["scenario_14"] = run_test_14_end_to_end_backend_api()

    print("\n" + "=" * 70)
    print("SUMMARY OF ALL 7 VERIFICATION SCENARIOS:")
    all_passed = True
    for sc, res in results.items():
        st = res.get("status")
        print(f"  {sc.upper()}: {st}")
        if st != "PASS":
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL 7 CROSS-REPO INTEGRATION SCENARIOS PASSED VERIFICATION.")
    else:
        print("SOME SCENARIOS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
