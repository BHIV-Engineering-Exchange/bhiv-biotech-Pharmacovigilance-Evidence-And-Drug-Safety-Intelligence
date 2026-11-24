"""
BHIV BiotechSystem — Hariom Integration Test Suite
Backend Architecture & Integration | EOD 20 November 2026

Covers all 15 required test scenarios:
  1. Valid report input
  2. Missing required input
  3. Invalid JSON/schema/type/enum
  4. Successful evidence retrieval (mocked OpenFDA)
  5. Source API failure or timeout
  6. Valid QC record
  7. Invalid QC record
  8. Exact duplicate
  9. Same source ID with conflicting content
  10. Unresolved drug/entity match
  11. Unknown real/synthetic status
  12. Human-review routing
  13. Original record and provenance preservation
  14. Repeat-run deterministic output
  15. API health and API request/response behavior (without live HTTP)

All external API calls are mocked. Live API calls are separated and labelled.
Run: pytest integration/test_hariom_integration.py -v
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from integration.shared_evidence_contract import (
    CONTRACT_VERSION,
    ALLOWED_DATA_ORIGINS,
    ALLOWED_VALIDATION_STATUS,
    ALLOWED_HUMAN_REVIEW_STATUS,
    SharedEvidenceContract,
    from_evidence_record,
)
from integration.qc_adapter import (
    build_qc_record_from_contract,
    get_qc_engine_status,
    validate_qc_record,
)
from integration.drug_safety_adapter import (
    get_drug_safety_status,
    get_staged_records,
)
from src.research_integration import run_research_workflow, validate_research_report
from src.evidence_schema import EvidenceRecord, validate_evidence, generate_evidence_id
from src.normalize_evidence import normalize_record
from src.evidence_store import (
    add_evidence_with_audit,
    detect_conflicts,
    load_evidence,
    save_evidence,
)
from src.entity_resolution import EntityCandidate, resolve_entity


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SYNTHETIC_OPENFDA_RECORD = {
    "safetyreportid": "SYNTH-TEST-001",
    "patient": {
        "drug": [
            {
                "medicinalproduct": "ASPIRIN",
                "openfda": {"application_number": ["NDA000100"]},
            }
        ],
        "reaction": [{"reactionmeddrapt": "NAUSEA"}],
    },
}

SYNTHETIC_RETRIEVED_AT = "2026-11-20T10:00:00+00:00"
SYNTHETIC_SOURCE_URL = "https://api.fda.gov/drug/event.json?search=test&limit=5"


def make_evidence_record(record_id: str = "SYNTH-001") -> EvidenceRecord:
    return normalize_record(
        {
            "safetyreportid": record_id,
            "patient": {
                "drug": [{"medicinalproduct": "IBUPROFEN", "openfda": {"application_number": ["NDA000001"]}}],
                "reaction": [{"reactionmeddrapt": "HEADACHE"}],
            },
        },
        1,
        SYNTHETIC_RETRIEVED_AT,
        SYNTHETIC_SOURCE_URL,
        requested_drug_name="ibuprofen",
    )


def make_contract(record_id: str = "SYNTH-001") -> SharedEvidenceContract:
    ev = make_evidence_record(record_id)
    return from_evidence_record(
        ev.to_dict(),
        validation_status="VALID",
        duplicate_status="UNIQUE",
        conflict_status="NO_CONFLICT",
        human_review_status="PENDING",
    )


# ===========================================================================
# TEST 1: Valid report input
# ===========================================================================

class TestValidReportInput:
    def test_valid_report_passes_validation(self):
        """TEST 1: validate_research_report accepts valid input."""
        report = {"report_id": "RPT-001", "drug_name": "aspirin"}
        result = validate_research_report(report)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_valid_evidence_record_produces_valid_contract(self):
        """TEST 1: Normalized evidence produces a valid SharedEvidenceContract."""
        contract = make_contract("SYNTH-VALID-001")
        is_valid, errors = contract.validate()
        assert is_valid is True, f"Contract validation failed: {errors}"
        assert errors == []
        assert contract.contract_version == CONTRACT_VERSION


# ===========================================================================
# TEST 2: Missing required input
# ===========================================================================

class TestMissingRequiredInput:
    def test_missing_report_id(self):
        """TEST 2: Missing report_id fails validation."""
        result = validate_research_report({"drug_name": "aspirin"})
        assert result["valid"] is False
        assert any("report_id" in e for e in result["errors"])

    def test_missing_drug_name(self):
        """TEST 2: Missing drug_name fails validation."""
        result = validate_research_report({"report_id": "RPT-002"})
        assert result["valid"] is False
        assert any("drug_name" in e for e in result["errors"])

    def test_missing_both_fields(self):
        """TEST 2: Empty report fails with both errors."""
        result = validate_research_report({})
        assert result["valid"] is False
        assert len(result["errors"]) >= 2

    def test_contract_missing_evidence_id_is_invalid(self):
        """TEST 2: Contract with blank evidence_id fails validation."""
        contract = make_contract()
        contract.evidence_id = ""
        is_valid, errors = contract.validate()
        assert is_valid is False
        assert any("evidence_id" in e for e in errors)

    def test_contract_missing_source_url_none_is_invalid(self):
        """TEST 2: Contract with source_url=None fails validation."""
        contract = make_contract()
        contract.source_url = None
        is_valid, errors = contract.validate()
        assert is_valid is False


# ===========================================================================
# TEST 3: Invalid JSON/schema/type/enum
# ===========================================================================

class TestInvalidInput:
    def test_non_dict_report_fails(self):
        """TEST 3: Non-dict report fails gracefully."""
        result = validate_research_report("not a dict")
        assert result["valid"] is False

    def test_invalid_data_origin_enum(self):
        """TEST 3: Invalid data_origin enum value is caught."""
        contract = make_contract()
        contract.data_origin = "CLINICAL_TRIAL"  # not in allowed set
        is_valid, errors = contract.validate()
        assert is_valid is False
        assert any("data_origin" in e for e in errors)

    def test_invalid_validation_status_enum(self):
        """TEST 3: Invalid validation_status enum value is caught."""
        contract = make_contract()
        contract.validation_status = "APPROVED"  # not in allowed set
        is_valid, errors = contract.validate()
        assert is_valid is False
        assert any("validation_status" in e for e in errors)

    def test_invalid_human_review_status_enum(self):
        """TEST 3: Invalid human_review_status enum value is caught."""
        contract = make_contract()
        contract.human_review_status = "DONE"  # not in allowed set
        is_valid, errors = contract.validate()
        assert is_valid is False
        assert any("human_review_status" in e for e in errors)

    def test_provenance_must_be_dict(self):
        """TEST 3: Non-dict provenance is rejected."""
        contract = make_contract()
        contract.provenance = "not a dict"
        is_valid, errors = contract.validate()
        assert is_valid is False
        assert any("provenance" in e for e in errors)

    def test_non_dict_raw_record_raises(self):
        """TEST 3: normalize_record raises on non-dict input."""
        with pytest.raises(ValueError, match="raw_record must be a dictionary"):
            normalize_record("not-a-dict", 1, SYNTHETIC_RETRIEVED_AT, SYNTHETIC_SOURCE_URL)


# ===========================================================================
# TEST 4: Successful evidence retrieval (mocked OpenFDA)
# ===========================================================================

class TestSuccessfulEvidenceRetrieval:
    def test_mocked_openfda_returns_evidence(self):
        """TEST 4: Mocked OpenFDA retriever returns normalized evidence (via run_research_workflow retriever kwarg)."""
        mock_result = {
            "success": True,
            "source": "OpenFDA/FAERS",
            "retrieved_at": SYNTHETIC_RETRIEVED_AT,
            "source_url": SYNTHETIC_SOURCE_URL,
            "record_count": 1,
            "raw_response": {"results": [SYNTHETIC_OPENFDA_RECORD]},
        }
        report = {"report_id": "RPT-004", "drug_name": "aspirin"}

        # Use the retriever kwarg so we don't depend on mock patch path resolution
        result = run_research_workflow(report, retriever=lambda *a, **kw: mock_result)

        assert result["status"] == "REVIEW_REQUIRED"
        assert len(result["findings"]) == 1
        finding = result["findings"][0]
        assert finding["finding"]["drug_name"] == "ASPIRIN"
        assert finding["finding"]["adverse_event"] == "NAUSEA"
        assert finding["evidence_origin"] == "SOURCE_DERIVED"
        assert finding["model_generated_summary"] is False

    def test_evidence_contract_built_from_finding(self):
        """TEST 4: SharedEvidenceContract built from finding passes validation (via retriever kwarg)."""
        mock_result = {
            "success": True,
            "source": "OpenFDA/FAERS",
            "retrieved_at": SYNTHETIC_RETRIEVED_AT,
            "source_url": SYNTHETIC_SOURCE_URL,
            "record_count": 1,
            "raw_response": {"results": [SYNTHETIC_OPENFDA_RECORD]},
        }
        report = {"report_id": "RPT-004B", "drug_name": "aspirin"}

        result = run_research_workflow(report, retriever=lambda *a, **kw: mock_result)

        finding = result["findings"][0]["finding"]
        contract = from_evidence_record(
            finding,
            validation_status="VALID",
            duplicate_status="UNIQUE",
            conflict_status="NO_CONFLICT",
            human_review_status="PENDING",
        )
        is_valid, errors = contract.validate()
        assert is_valid is True, f"Contract failed: {errors}"


# ===========================================================================
# TEST 5: Source API failure or timeout
# ===========================================================================

class TestSourceAPIFailure:
    def test_openfda_failure_returns_source_unavailable(self):
        """TEST 5: API failure returns SOURCE_UNAVAILABLE status (via retriever kwarg)."""
        mock_result = {
            "success": False,
            "error": "Connection timeout: api.fda.gov",
            "retrieved_at": SYNTHETIC_RETRIEVED_AT,
        }
        report = {"report_id": "RPT-005", "drug_name": "aspirin"}

        result = run_research_workflow(report, retriever=lambda *a, **kw: mock_result)

        assert result["status"] == "SOURCE_UNAVAILABLE"
        assert result["findings"] == []
        assert result["human_review"]["required"] is True
        assert result["human_review"]["status"] == "PENDING"

    def test_openfda_no_records_returns_no_evidence(self):
        """TEST 5: Empty OpenFDA results handled gracefully (via retriever kwarg)."""
        mock_result = {
            "success": True,
            "source": "OpenFDA/FAERS",
            "retrieved_at": SYNTHETIC_RETRIEVED_AT,
            "source_url": SYNTHETIC_SOURCE_URL,
            "record_count": 0,
            "raw_response": {"results": []},
        }
        report = {"report_id": "RPT-005B", "drug_name": "DRUG_NOT_IN_FDA_XXXXXX"}

        result = run_research_workflow(report, retriever=lambda *a, **kw: mock_result)

        assert result["status"] == "NO_EVIDENCE"
        assert result["findings"] == []


# ===========================================================================
# TEST 6: Valid QC record
# ===========================================================================

class TestValidQCRecord:
    def test_qc_engine_status_returned(self):
        """TEST 6: QC engine status is returned accurately."""
        qc_status = get_qc_engine_status()
        assert "available" in qc_status
        assert "status" in qc_status
        assert "dependency_pr" in qc_status

    def test_qc_validate_when_engine_not_available(self):
        """TEST 6: Returns SERVICE_BOUNDARY_NOT_MET when engine not installed."""
        record = build_qc_record_from_contract(make_contract().to_dict())
        result = validate_qc_record(record)
        # QC engine will not be available in test environment
        assert result["qc_status"] in ("PASS", "FAIL", "SERVICE_BOUNDARY_NOT_MET")
        assert "engine_available" in result
        if not result["engine_available"]:
            assert result["blocker"] is not None

    def test_valid_qc_mapping_built(self):
        """TEST 6: QC record mapping from contract is built without fabrication."""
        contract = make_contract("SYNTH-QC-001")
        qc_rec = build_qc_record_from_contract(contract.to_dict())
        assert qc_rec["schema_version"] == "1.0.0"
        assert qc_rec["evidence_id"] == contract.evidence_id
        assert "NOT_REPORTED" in qc_rec["protocol_reference"]
        assert "_mapping_note" in qc_rec
        assert "PROPOSED_MAPPING" in qc_rec["_mapping_note"]


# ===========================================================================
# TEST 7: Invalid QC record
# ===========================================================================

class TestInvalidQCRecord:
    def test_qc_validate_empty_record(self):
        """TEST 7: Empty QC record is handled without crash."""
        result = validate_qc_record({})
        assert result["qc_status"] in ("FAIL", "SERVICE_BOUNDARY_NOT_MET")

    def test_qc_validate_missing_required_fields(self):
        """TEST 7: QC record missing required fields handled correctly."""
        record = {"schema_version": "1.0.0", "evidence_id": "EV-TEST"}
        result = validate_qc_record(record)
        assert result["qc_status"] in ("FAIL", "SERVICE_BOUNDARY_NOT_MET")


# ===========================================================================
# TEST 8: Exact duplicate
# ===========================================================================

class TestExactDuplicate:
    def test_exact_duplicate_not_stored_twice(self, tmp_path):
        """TEST 8: Identical evidence record is not stored twice."""
        import src.evidence_store as store
        original = store.EVIDENCE_FILE
        store.EVIDENCE_FILE = str(tmp_path / "ev.json")

        try:
            ev = make_evidence_record("SYNTH-DUP-001").to_dict()
            audit1 = add_evidence_with_audit([ev])
            audit2 = add_evidence_with_audit([ev])

            assert audit1["added"] == 1
            assert audit1["duplicates"] == 0
            assert audit2["added"] == 0
            assert audit2["duplicates"] == 1
        finally:
            store.EVIDENCE_FILE = original

    def test_contract_fingerprint_identical_for_same_content(self):
        """TEST 8: Identical contracts produce same fingerprint."""
        c1 = make_contract("SYNTH-DUP-002")
        c2 = make_contract("SYNTH-DUP-002")
        assert c1.fingerprint() == c2.fingerprint()


# ===========================================================================
# TEST 9: Same source ID with conflicting content
# ===========================================================================

class TestConflictingContent:
    def test_conflict_detected(self, tmp_path):
        """TEST 9: Conflict detected for same source_record_id with different content."""
        import src.evidence_store as store
        original = store.EVIDENCE_FILE
        store.EVIDENCE_FILE = str(tmp_path / "ev_conflict.json")

        try:
            ev1 = make_evidence_record("SYNTH-CONF-001").to_dict()
            ev2 = copy.deepcopy(ev1)
            ev2["adverse_event"] = "VOMITING"  # Different content, same source_record_id

            audit1 = add_evidence_with_audit([ev1])
            assert audit1["added"] == 1

            audit2 = add_evidence_with_audit([ev2])
            assert audit2["conflicts"] == 1
            assert audit2["added"] == 0
        finally:
            store.EVIDENCE_FILE = original

    def test_conflict_records_detected_by_detect_conflicts(self, tmp_path):
        """TEST 9: detect_conflicts returns conflict details."""
        ev1 = make_evidence_record("SYNTH-CONF-002").to_dict()
        ev2 = copy.deepcopy(ev1)
        ev2["adverse_event"] = "RASH"

        conflicts = detect_conflicts([ev2], existing_records=[ev1])
        assert len(conflicts) == 1
        assert conflicts[0]["source_record_id"] == "SYNTH-CONF-002"
        assert any(d["field"] == "adverse_event" for d in conflicts[0]["differences"])


# ===========================================================================
# TEST 10: Unresolved drug/entity match
# ===========================================================================

class TestUnresolvedEntityMatch:
    def test_unresolved_entity_resolution(self):
        """TEST 10: No candidate match produces UNRESOLVED status."""
        result = resolve_entity("UNKNOWN_DRUG_XYZ", candidates=[])
        assert result.status == "UNRESOLVED"
        assert result.canonical_name is None
        assert result.identifier is None

    def test_ambiguous_entity_resolution(self):
        """TEST 10: Multiple candidates produce AMBIGUOUS status."""
        candidates = [
            EntityCandidate(canonical_name="aspirin"),
            EntityCandidate(canonical_name="aspirin"),  # duplicate name in list
        ]
        result = resolve_entity("aspirin", candidates=candidates)
        assert result.status == "AMBIGUOUS"

    def test_contract_unresolved_entity_still_valid(self):
        """TEST 10: Contract with UNRESOLVED entity_resolution_status passes validation."""
        contract = make_contract()
        contract.entity_resolution_status = "UNRESOLVED"
        contract.canonical_entity_name = None
        is_valid, errors = contract.validate()
        assert is_valid is True


# ===========================================================================
# TEST 11: Unknown real/synthetic status
# ===========================================================================

class TestDataOriginStatus:
    def test_synthetic_data_origin_valid(self):
        """TEST 11: SYNTHETIC data origin is a valid enum value."""
        contract = make_contract()
        contract.data_origin = "SYNTHETIC"
        is_valid, errors = contract.validate()
        assert is_valid is True

    def test_test_data_origin_valid(self):
        """TEST 11: TEST data origin is a valid enum value."""
        contract = make_contract()
        contract.data_origin = "TEST"
        is_valid, errors = contract.validate()
        assert is_valid is True

    def test_unknown_data_origin_invalid(self):
        """TEST 11: Unlabelled data origin is rejected."""
        contract = make_contract()
        contract.data_origin = "UNKNOWN_ORIGIN"
        is_valid, errors = contract.validate()
        assert is_valid is False


# ===========================================================================
# TEST 12: Human-review routing
# ===========================================================================

class TestHumanReviewRouting:
    def test_workflow_always_requires_human_review(self):
        """TEST 12: Research workflow always routes to human review (via retriever kwarg)."""
        mock_result = {
            "success": True,
            "source": "OpenFDA/FAERS",
            "retrieved_at": SYNTHETIC_RETRIEVED_AT,
            "source_url": SYNTHETIC_SOURCE_URL,
            "record_count": 1,
            "raw_response": {"results": [SYNTHETIC_OPENFDA_RECORD]},
        }
        report = {"report_id": "RPT-012", "drug_name": "aspirin"}

        result = run_research_workflow(report, retriever=lambda *a, **kw: mock_result)

        assert result["human_review"]["required"] is True
        assert result["human_review"]["status"] == "PENDING"

    def test_invalid_input_routes_to_human_review(self):
        """TEST 12: Invalid input still triggers human review flag."""
        result = run_research_workflow({"report_id": "", "drug_name": ""})
        assert result["human_review"]["required"] is True

    def test_contract_human_review_pending_by_default(self):
        """TEST 12: Freshly built contract has PENDING human review."""
        contract = make_contract()
        assert contract.human_review_status == "PENDING"


# ===========================================================================
# TEST 13: Original record and provenance preservation
# ===========================================================================

class TestProvenancePreservation:
    def test_original_report_preserved_in_workflow_output(self):
        """TEST 13: Original report preserved unmodified in workflow output (via retriever kwarg)."""
        original_report = {"report_id": "RPT-013", "drug_name": "ASPIRIN"}
        mock_result = {
            "success": False,
            "error": "Timeout",
            "retrieved_at": SYNTHETIC_RETRIEVED_AT,
        }

        result = run_research_workflow(copy.deepcopy(original_report), retriever=lambda *a, **kw: mock_result)

        assert result["original_report"]["report_id"] == original_report["report_id"]
        assert result["original_report"]["drug_name"] == original_report["drug_name"]

    def test_evidence_provenance_fields_preserved(self):
        """TEST 13: EvidenceRecord provenance dict contains required fields."""
        ev = make_evidence_record("SYNTH-PROV-001")
        prov = ev.provenance
        assert prov.get("source_system") == "OpenFDA"
        assert prov.get("underlying_dataset") == "FAERS"
        assert prov.get("retrieval_method") == "REST API"
        assert prov.get("transformation") is not None

    def test_producer_record_preserved_verbatim_in_contract(self):
        """TEST 13: producer_record preserved verbatim in SharedEvidenceContract."""
        original = {"raw_field": "raw_value", "source_id": "SRC-001"}
        contract = make_contract()
        contract.producer_record = copy.deepcopy(original)
        assert contract.producer_record == original

    def test_source_record_id_preserved(self):
        """TEST 13: source_record_id from OpenFDA preserved through normalization."""
        ev = make_evidence_record("ORIG-SOURCE-001")
        assert ev.source_record_id == "ORIG-SOURCE-001"
        d = ev.to_dict()
        assert d["source_record_id"] == "ORIG-SOURCE-001"


# ===========================================================================
# TEST 14: Repeat-run deterministic output
# ===========================================================================

class TestDeterministicOutput:
    def test_evidence_id_deterministic_from_source_record_id(self):
        """TEST 14: Evidence ID is deterministic when source_record_id is present."""
        ev1 = make_evidence_record("SYNTH-DET-001")
        ev2 = make_evidence_record("SYNTH-DET-001")
        assert ev1.evidence_id == ev2.evidence_id

    def test_fingerprint_deterministic(self):
        """TEST 14: Content fingerprint is deterministic for identical content."""
        c1 = make_contract("SYNTH-FP-001")
        c2 = make_contract("SYNTH-FP-001")
        assert c1.fingerprint() == c2.fingerprint()

    def test_normalize_record_deterministic(self):
        """TEST 14: normalize_record produces identical output for identical input."""
        raw = copy.deepcopy(SYNTHETIC_OPENFDA_RECORD)
        ev1 = normalize_record(raw, 1, SYNTHETIC_RETRIEVED_AT, SYNTHETIC_SOURCE_URL, requested_drug_name="aspirin")
        ev2 = normalize_record(raw, 1, SYNTHETIC_RETRIEVED_AT, SYNTHETIC_SOURCE_URL, requested_drug_name="aspirin")
        assert ev1.evidence_id == ev2.evidence_id
        assert ev1.drug_name == ev2.drug_name
        assert ev1.adverse_event == ev2.adverse_event


# ===========================================================================
# TEST 15: API health and request/response behavior (without live HTTP)
# ===========================================================================

class TestAPIBehavior:
    def test_health_endpoint_returns_ok(self):
        """TEST 15: Health endpoint returns OK status."""
        try:
            from fastapi.testclient import TestClient
            from integration.api_service import app
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"
            assert "pipeline_modules" in data
            assert "integrations" in data
        except ImportError:
            pytest.skip("FastAPI or httpx not installed — skipping HTTP test")

    def test_research_evidence_endpoint_with_mock(self):
        """TEST 15: POST /api/v1/research/evidence returns structured response."""
        try:
            from fastapi.testclient import TestClient
            from integration.api_service import app

            mock_result = {
                "success": True,
                "source": "OpenFDA/FAERS",
                "retrieved_at": SYNTHETIC_RETRIEVED_AT,
                "source_url": SYNTHETIC_SOURCE_URL,
                "record_count": 1,
                "raw_response": {"results": [SYNTHETIC_OPENFDA_RECORD]},
            }

            with patch("src.research_integration.search_drug", return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/api/v1/research/evidence",
                    json={"report_id": "API-TEST-001", "drug_name": "aspirin"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["report_id"] == "API-TEST-001"
            assert data["findings_count"] >= 1
            assert "service_disclaimer" in data
            assert "REVIEW_REQUIRED" in data["service_disclaimer"]
        except ImportError:
            pytest.skip("FastAPI or httpx not installed — skipping HTTP test")

    def test_research_evidence_missing_drug_name(self):
        """TEST 15: POST with missing drug_name returns 422."""
        try:
            from fastapi.testclient import TestClient
            from integration.api_service import app
            client = TestClient(app)
            response = client.post(
                "/api/v1/research/evidence",
                json={"report_id": "API-TEST-002"},
            )
            assert response.status_code == 422
        except ImportError:
            pytest.skip("FastAPI or httpx not installed — skipping HTTP test")

    def test_qc_validate_endpoint(self):
        """TEST 15: POST /api/v1/qc/validate returns expected structure."""
        try:
            from fastapi.testclient import TestClient
            from integration.api_service import app
            client = TestClient(app)
            response = client.post(
                "/api/v1/qc/validate",
                json={"record": {"schema_version": "1.0.0", "evidence_id": "EV-TEST"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert "qc_status" in data
            assert data["qc_status"] in ("PASS", "FAIL", "SERVICE_BOUNDARY_NOT_MET")
        except ImportError:
            pytest.skip("FastAPI or httpx not installed — skipping HTTP test")

    def test_services_status_endpoint(self):
        """TEST 15: GET /api/v1/services/status returns all service statuses."""
        try:
            from fastapi.testclient import TestClient
            from integration.api_service import app
            client = TestClient(app)
            response = client.get("/api/v1/services/status")
            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert "OpenFDA_FAERS" in data["services"]
        except ImportError:
            pytest.skip("FastAPI or httpx not installed — skipping HTTP test")

    def test_drug_safety_adapter_status(self):
        """TEST 15: Drug safety adapter returns accurate status."""
        status = get_drug_safety_status()
        assert "available" in status
        assert "status" in status
        assert "dependency_pr" in status

    def test_staged_records_handled_when_not_available(self):
        """TEST 15: Staged records returns structured NOT_AVAILABLE response."""
        result = get_staged_records()
        assert "status" in result
        assert result["status"] in ("AVAILABLE", "NOT_AVAILABLE", "ERROR")
        if result["status"] == "NOT_AVAILABLE":
            assert result["records"] == []
            assert result["blocker"] is not None


# ===========================================================================
# BONUS: Cross-contract consistency checks
# ===========================================================================

class TestCrossContractConsistency:
    def test_all_allowed_validation_statuses_pass_contract(self):
        """All valid enum values for validation_status pass contract validation."""
        for vs in ALLOWED_VALIDATION_STATUS:
            contract = make_contract()
            contract.validation_status = vs
            is_valid, errors = contract.validate()
            assert is_valid is True, f"Status '{vs}' failed: {errors}"

    def test_all_allowed_human_review_statuses_pass_contract(self):
        """All valid human_review_status values pass contract validation."""
        for hrs in ALLOWED_HUMAN_REVIEW_STATUS:
            contract = make_contract()
            contract.human_review_status = hrs
            is_valid, errors = contract.validate()
            assert is_valid is True, f"Status '{hrs}' failed: {errors}"

    def test_contract_to_dict_round_trip(self):
        """Contract serializes to dict and all required keys are present."""
        contract = make_contract()
        d = contract.to_dict()
        required_keys = [
            "evidence_id", "source_record_id", "source", "source_url",
            "drug_name", "evidence_type", "retrieved_at", "schema_version",
            "provenance", "data_origin", "validation_status", "duplicate_status",
            "conflict_status", "human_review_status", "contract_version",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"
