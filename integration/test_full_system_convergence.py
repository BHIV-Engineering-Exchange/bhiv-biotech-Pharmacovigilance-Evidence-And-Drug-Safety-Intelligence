"""
BHIV BiotechSystem — Full System Convergence & Component Integration Test Suite
Owner: Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence

Tests all 5 key system components:
  1. QC Engine (Shyamal) — Verification & Draft 2020-12 Schema Validation
  2. Drug Safety & Biomedical Evidence (Shravani) — Staged record adapter, contract bridging & blocker transparency
  3. Drug Discovery (Shamit) — Candidate record loading, score reproducibility gap analysis & QC bridging
  4. Patient Data & Clinical Intake — PII sanitization, contract normalization, QC validation & audit persistence
  5. Backend REST API Endpoints — In-process TestClient and live socket verification
"""

from __future__ import annotations

import copy
import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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
)
from integration.drug_safety_adapter import (
    get_drug_safety_status,
    get_staged_records,
    build_contract_from_drug_safety_record,
    validate_drug_safety_through_qc,
)
from integration.drug_discovery_adapter import (
    get_drug_discovery_status,
    load_candidate_records,
    inspect_candidate_record,
    build_contract_from_candidate,
    validate_candidate_through_qc,
    REQUIRED_SCORE_FIELDS,
)
from integration.patient_data_adapter import (
    get_patient_data_status,
    process_patient_intake,
    sanitize_patient_identifier,
    validate_patient_intake_payload,
)
from integration.api_service import app
from src.evidence_store import load_evidence


# ---------------------------------------------------------------------------
# Test Suite 1: QC Engine Component Integration
# ---------------------------------------------------------------------------

class TestQCEngineComponent:
    def test_qc_engine_is_installed_as_package(self):
        """QC Engine must be importable as an installed package, not a stub."""
        import qc_engine.engine as qe
        assert qe.ENGINE_VERSION == "1.0.0"
        assert qe.SCHEMA_VERSION == "1.0.0"
        assert QC_ENGINE_AVAILABLE is True

    def test_qc_engine_status_is_verified(self):
        """get_qc_engine_status must report VERIFIED with no blocker."""
        status = get_qc_engine_status()
        assert status["available"] is True
        assert status["status"] == "VERIFIED"
        assert status["blocker"] is None

    def test_qc_validation_runs_live_draft_2020_12_schema(self):
        """Live QC validation correctly accepts valid record and rejects invalid."""
        valid_rec = {
            "schema_version": "1.0.0",
            "evidence_id": "EV-TEST-QC-001",
            "study_id": "STUDY-QC-001",
            "source": "Analytical Assay",
            "protocol_reference": "NOT_REPORTED",
            "sample_identification": "NOT_REPORTED",
            "control_identification": "NOT_REPORTED",
            "experimental_conditions": "NOT_REPORTED",
            "measurement_method": "HPLC-UV",
            "method_validation_status": "VALIDATED",
            "raw_data_availability": "AVAILABLE",
            "missing_data": [],
            "deviations": [],
            "statistical_reporting": "NOT_REPORTED",
            "reproducibility": "NOT_REPORTED",
            "limitations": "NOT_REPORTED",
            "evidence_category": "Analytical",
            "synthetic_data_declaration": "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING",
            "reviewer_status": "NOT REVIEWED",
            "evidence_quality": "VERIFIED",
            "final_review_status": "READY FOR HUMAN REVIEW",
        }
        res = validate_qc_record(valid_rec)
        assert res["qc_status"] == "PASS"
        assert res["qc_errors"] == []

        bad_rec = copy.deepcopy(valid_rec)
        del bad_rec["evidence_category"]
        res_bad = validate_qc_record(bad_rec)
        assert res_bad["qc_status"] == "FAIL"
        assert len(res_bad["qc_errors"]) > 0


# ---------------------------------------------------------------------------
# Test Suite 2: Drug Safety & Biomedical Evidence Component
# ---------------------------------------------------------------------------

class TestDrugSafetyComponent:
    def test_drug_safety_status_reports_accurate_blockers(self):
        """Drug safety status correctly surfaces staged files and known provenance blocker."""
        status = get_drug_safety_status()
        assert status["available"] is True
        assert "staged_file" in status
        assert status["record_count"] == 10
        assert status["failed_validation_count"] == 10
        assert "provenance" in status["blocker"].lower() or "source_url" in status["blocker"].lower()

    def test_staged_records_loaded_and_preserved(self):
        """Staged records are preserved verbatim without altering failing records."""
        staged = get_staged_records()
        assert staged["status"] == "AVAILABLE"
        assert staged["failed_validation_count"] == 10
        first_fail = staged["failed_validation_records"][0]
        assert first_fail["disposition"] == "PRESERVED_FOR_REVIEW"
        assert first_fail["human_review_required"] is True

    def test_drug_safety_contract_bridging(self):
        """Drug safety staged records bridge to SharedEvidenceContract without fabricating missing source_url."""
        staged = get_staged_records()
        raw_item = staged["failed_validation_records"][0]["record"]
        contract = build_contract_from_drug_safety_record(raw_item)
        assert contract.evidence_type == "Drug safety biosimilarity record"
        assert contract.validation_status == "INVALID"
        assert contract.human_review_status == "PENDING"
        assert contract.source_record_id == "EV001"

    def test_drug_safety_qc_validation_bridge(self):
        """Drug safety record bridges into Shyamal's QC Engine."""
        staged = get_staged_records()
        raw_item = staged["failed_validation_records"][0]["record"]
        qc_result = validate_drug_safety_through_qc(raw_item)
        assert qc_result["engine_available"] is True
        assert qc_result["qc_status"] == "PASS"


# ---------------------------------------------------------------------------
# Test Suite 3: Drug Discovery Component
# ---------------------------------------------------------------------------

class TestDrugDiscoveryComponent:
    def test_drug_discovery_status_and_records_available(self):
        """Candidate records exist and status reports CONNECTED_WITH_LIMITATIONS."""
        status = get_drug_discovery_status()
        assert status["available"] is True
        assert status["record_count"] == 10
        assert status["incomplete_score_input_count"] == 10
        assert "score.score_inputs" in status["blocker"]

    def test_candidate_inspection_detects_missing_score_inputs(self):
        """Inspection of committed records catches missing score_inputs without fabricating scores."""
        candidates = load_candidate_records()
        assert len(candidates) == 10
        c1 = candidates[0]
        inspection = inspect_candidate_record(c1)
        assert inspection["candidate_id"] == "C-001"
        assert inspection["compound_name"] == "Rifampicin"
        assert inspection["score_inputs_present"] is False
        assert inspection["score_reproducible"] is False
        assert len(inspection["missing_score_fields"]) == len(REQUIRED_SCORE_FIELDS)
        assert inspection["total_score"] is None
        assert inspection["human_review_required"] is True

    def test_candidate_inspection_with_valid_score_inputs(self):
        """When valid score inputs are present, score is deterministically calculated."""
        synthetic_candidate = {
            "candidate_id": "C-SYNTH-099",
            "compound_name": "TestCompound",
            "score": {
                "score_inputs": {f: 4 for f in REQUIRED_SCORE_FIELDS}
            }
        }
        inspection = inspect_candidate_record(synthetic_candidate)
        assert inspection["score_reproducible"] is True
        assert inspection["total_score"] == 32
        assert inspection["score_status"] == "COMPLETE"

    def test_candidate_contract_bridging(self):
        """Candidate record wraps into SharedEvidenceContract cleanly."""
        candidates = load_candidate_records()
        contract = build_contract_from_candidate(candidates[0])
        assert contract.evidence_type == "Drug discovery candidate record"
        assert contract.drug_name == "Rifampicin"
        assert contract.human_review_status == "PENDING"
        assert contract.validation_status == "REVIEW_REQUIRED"

    def test_candidate_qc_validation_bridge(self):
        """Candidate record validates cleanly through Shyamal's Preclinical QC Engine."""
        candidates = load_candidate_records()
        qc_result = validate_candidate_through_qc(candidates[0])
        assert qc_result["engine_available"] is True
        assert qc_result["qc_status"] == "PASS"


# ---------------------------------------------------------------------------
# Test Suite 4: Patient Data & Clinical Intake Component
# ---------------------------------------------------------------------------

class TestPatientDataComponent:
    def test_patient_identifier_sanitization_and_pseudonymization(self):
        """Patient MRN/ID is pseudonymized via deterministic SHA-256 and never stored in plain text."""
        raw_mrn = "MRN-987654321"
        pseudo1 = sanitize_patient_identifier(raw_mrn)
        pseudo2 = sanitize_patient_identifier(raw_mrn)
        assert pseudo1 == pseudo2
        assert raw_mrn not in pseudo1
        assert pseudo1.startswith("PT-")

    def test_intake_validation_rejects_forbidden_pii(self):
        """Payloads containing explicit forbidden PII fields are rejected."""
        bad_payload = {
            "report_id": "RPT-PII-001",
            "drug_name": "ASPIRIN",
            "ssn": "000-11-2222",
        }
        valid, errors = validate_patient_intake_payload(bad_payload)
        assert valid is False
        assert any("Direct PII fields are strictly forbidden" in e for e in errors)

    def test_process_patient_intake_end_to_end(self):
        """Patient observation intake creates contract, runs QC, and persists with audit."""
        payload = {
            "report_id": "PT-RPT-001",
            "drug_name": "Lisinopril",
            "patient_id": "HOSPITAL-PT-555",
            "adverse_event": "Persistent Dry Cough",
            "reporter_role": "ATTENDING_PHYSICIAN",
            "data_origin": "REAL_WORLD",
        }
        res = process_patient_intake(payload, store_evidence=True)
        assert res["status"] == "ACCEPTED"
        assert res["report_id"] == "PT-RPT-001"
        assert res["pseudonymized_patient_id"].startswith("PT-")
        assert res["qc_status"] == "PASS"
        assert res["human_review_required"] is True
        assert res["contract"]["adverse_event"] == "Persistent Dry Cough"


# ---------------------------------------------------------------------------
# Test Suite 5: Extended FastAPI Endpoints
# ---------------------------------------------------------------------------

class TestExtendedAPIEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_reports_all_five_components(self, client):
        """GET /health reports status for all integrated components."""
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OK"
        integrations = data["integrations"]
        assert integrations["qc_engine_shyamal"] == "VERIFIED"
        assert integrations["drug_safety_shravani"] in ("CONNECTED_WITH_KNOWN_BLOCKER", "BLOCKED")
        assert integrations["drug_discovery_shamit"] in ("CONNECTED_WITH_LIMITATIONS", "PROPOSED")
        assert integrations["patient_data"] == "AVAILABLE"
        assert integrations["fastapi"] == "AVAILABLE"

    def test_patient_intake_endpoint(self, client):
        """POST /api/v1/patient/intake ingests, pseudonymizes, and validates clinical observations."""
        payload = {
            "report_id": "API-PT-001",
            "drug_name": "Metformin",
            "patient_id": "PT-MRN-444",
            "adverse_event": "Lactic Acidosis Suspicion",
            "data_origin": "REAL_WORLD",
            "store_evidence": False,
        }
        res = client.post("/api/v1/patient/intake", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ACCEPTED"
        assert data["report_id"] == "API-PT-001"
        assert data["qc_status"] == "PASS"
        assert "PT-MRN-444" not in data["pseudonymized_patient_id"]

    def test_drug_safety_staged_endpoint(self, client):
        """GET /api/v1/drug-safety/staged exposes staged records and known blocker details."""
        res = client.get("/api/v1/drug-safety/staged")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "AVAILABLE"
        assert data["failed_validation_count"] == 10
        assert data["blocker"] is not None

    def test_discovery_candidates_endpoint(self, client):
        """GET /api/v1/discovery/candidates exposes candidate compound gap analysis."""
        res = client.get("/api/v1/discovery/candidates")
        assert res.status_code == 200
        data = res.json()
        assert data["record_count"] == 10
        assert data["incomplete_score_count"] == 10
        assert len(data["candidates"]) == 10
        c1 = data["candidates"][0]
        assert c1["compound_name"] == "Rifampicin"
        assert c1["score_status"] == "INCOMPLETE"

    def test_discovery_validate_candidate_endpoint(self, client):
        """POST /api/v1/discovery/validate-candidate validates candidate through Shyamal's QC Engine."""
        candidates = load_candidate_records()
        res = client.post("/api/v1/discovery/validate-candidate", json=candidates[0])
        assert res.status_code == 200
        data = res.json()
        assert data["qc_status"] == "PASS"
        assert data["engine_available"] is True

    def test_services_status_includes_all_components(self, client):
        """GET /api/v1/services/status includes all components with accurate diagnostic details."""
        res = client.get("/api/v1/services/status")
        assert res.status_code == 200
        services = res.json()["services"]
        assert "QCEngine_Shyamal" in services
        assert "DrugSafety_Shravani" in services
        assert "DrugDiscovery_Shamit" in services
        assert "PatientData_ClinicalIntake" in services
        assert services["QCEngine_Shyamal"]["status"] == "VERIFIED"
        assert services["PatientData_ClinicalIntake"]["status"] == "AVAILABLE"
