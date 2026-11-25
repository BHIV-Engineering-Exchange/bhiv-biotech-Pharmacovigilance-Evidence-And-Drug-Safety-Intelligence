"""
BHIV BiotechSystem — Hariom Backend FastAPI Service
Backend Architecture & Integration | EOD 20 November 2026

Minimal, maintainable FastAPI REST service wrapping the existing
pharmacovigilance pipeline modules.

This service does NOT replace or rebuild the existing pipeline.
It exposes it through HTTP endpoints for Sarvesh's seven portals.

Startup:
    pip install fastapi uvicorn
    uvicorn integration.api_service:app --host 0.0.0.0 --port 8000 --reload

Health check:
    GET http://localhost:8000/health

Evidence endpoint:
    POST http://localhost:8000/api/v1/research/evidence
    Body: { "report_id": "RPT001", "drug_name": "aspirin" }

SAFETY NOTE:
    This service does not expose patient PII.
    All findings are labelled REVIEW_REQUIRED and require independent clinical review.
    It does not establish causality, diagnose conditions or recommend treatment.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow import of root-level src modules
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from fastapi import FastAPI, HTTPException, status
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field, field_validator
    FASTAPI_AVAILABLE = True
else:
    try:
        from fastapi import FastAPI, HTTPException, status
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field, field_validator
        FASTAPI_AVAILABLE = True
    except ImportError:
        FASTAPI_AVAILABLE = False
        # Provide stubs so the module can be imported for testing without FastAPI
        class FastAPI:  # type: ignore
            def __init__(self, *a, **kw): pass
            def get(self, *a, **kw): return lambda f: f
            def post(self, *a, **kw): return lambda f: f
        class HTTPException(Exception):  # type: ignore
            def __init__(self, status_code=500, detail=None): pass
        class BaseModel:  # type: ignore
            def __init__(self, *a, **kw): pass
        def Field(*a, **kw):  # type: ignore
            return None
        def field_validator(*a, **kw):  # type: ignore
            return lambda f: f
        class JSONResponse:  # type: ignore
            def __init__(self, *a, **kw): pass
        status = type("status", (), {"HTTP_200_OK": 200, "HTTP_404_NOT_FOUND": 404})()

from src.research_integration import run_research_workflow, validate_research_report
from src.evidence_schema import validate_evidence
from src.evidence_store import load_evidence, add_evidence_with_audit, detect_conflicts
from src.monitoring import log_event

from integration.shared_evidence_contract import (
    SharedEvidenceContract,
    from_evidence_record,
    CONTRACT_VERSION,
)
from integration.qc_adapter import validate_qc_record, get_qc_engine_status
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
)
from integration.patient_data_adapter import (
    get_patient_data_status,
    process_patient_intake,
    sanitize_patient_identifier,
)

# ---------------------------------------------------------------------------
# App instantiation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BHIV BiotechSystem — Pharmacovigilance Backend API",
    description=(
        "Backend API for BHIV Pharmacovigilance Evidence and Drug Safety Intelligence Pipeline. "
        "Owner: Hariom Upadhyay (Backend Architecture & Integration). "
        "Findings are REVIEW_REQUIRED and do not constitute clinical advice."
    ),
    version="1.0.0",
)

SERVICE_START_TIME = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    started_at: str
    timestamp: str
    pipeline_modules: Dict[str, str]
    integrations: Dict[str, str]


class EvidenceRequest(BaseModel):
    report_id: str = Field(..., min_length=1, description="Unique report identifier")
    drug_name: str = Field(..., min_length=1, description="Drug name to search")
    limit: int = Field(default=5, ge=1, le=20, description="Max evidence records to retrieve")
    data_origin: str = Field(
        default="REAL_WORLD",
        description="Data origin: REAL_WORLD | SYNTHETIC | TEST | BENCHMARK",
    )

    @field_validator("data_origin")
    @classmethod
    def validate_data_origin(cls, v):
        allowed = {"REAL_WORLD", "SYNTHETIC", "TEST", "BENCHMARK"}
        if v not in allowed:
            raise ValueError(f"data_origin must be one of {sorted(allowed)}")
        return v

    @field_validator("report_id", "drug_name")
    @classmethod
    def not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("Must not be blank")
        return v.strip()


class EvidenceContractResponse(BaseModel):
    report_id: str
    drug_name: str
    status: str
    contract_version: str
    findings_count: int
    findings: List[Dict[str, Any]]
    uncertainty: Dict[str, Any]
    human_review: Dict[str, Any]
    service_disclaimer: str


class QCValidateRequest(BaseModel):
    record: Dict[str, Any] = Field(..., description="QC evidence record conforming to QC schema v1.0.0")


class QCValidateResponse(BaseModel):
    qc_status: str
    qc_errors: List[str]
    engine_available: bool
    engine_version: Optional[str]
    blocker: Optional[str]


class EvidenceGetResponse(BaseModel):
    evidence_id: str
    record: Optional[Dict[str, Any]]
    found: bool
    human_review_status: str
    disclaimer: str


class PatientIntakeRequest(BaseModel):
    report_id: str = Field(..., min_length=1, description="Unique clinical report ID")
    drug_name: str = Field(..., min_length=1, description="Administered drug name")
    patient_id: Optional[str] = Field(default=None, description="Patient MRN or ID (pseudonymized on ingest)")
    adverse_event: Optional[str] = Field(default="UNSPECIFIED_OBSERVATION", description="Observed clinical symptom/reaction")
    reporter_role: Optional[str] = Field(default="HEALTHCARE_PROFESSIONAL", description="Clinical reporter role")
    data_origin: Optional[str] = Field(default="REAL_WORLD", description="REAL_WORLD | SYNTHETIC | TEST")
    store_evidence: Optional[bool] = Field(default=True, description="Whether to persist in evidence store")


class PatientIntakeResponse(BaseModel):
    status: str
    report_id: str
    pseudonymized_patient_id: str
    contract: Optional[Dict[str, Any]]
    qc_status: Optional[str]
    qc_result: Optional[Dict[str, Any]]
    stored: bool
    human_review_required: bool
    service_disclaimer: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """
    System health check.
    Returns service status, module availability and integration statuses.
    """
    qc_status = get_qc_engine_status()
    ds_status = get_drug_safety_status()
    disc_status = get_drug_discovery_status()
    pt_status = get_patient_data_status()

    return HealthResponse(
        status="OK",
        service="BHIV Pharmacovigilance Backend API",
        version="1.0.0",
        started_at=SERVICE_START_TIME,
        timestamp=datetime.now(timezone.utc).isoformat(),
        pipeline_modules={
            "openfda_connector": "AVAILABLE",
            "normalize_evidence": "AVAILABLE",
            "evidence_schema": "AVAILABLE",
            "evidence_store": "AVAILABLE",
            "entity_resolution": "AVAILABLE",
            "research_integration": "AVAILABLE",
            "monitoring": "AVAILABLE",
            "error_handler": "AVAILABLE",
        },
        integrations={
            "qc_engine_shyamal": qc_status["status"],
            "drug_safety_shravani": ds_status["status"],
            "drug_discovery_shamit": disc_status["status"],
            "patient_data": pt_status["status"],
            "fastapi": "AVAILABLE" if FASTAPI_AVAILABLE else "NOT_INSTALLED",
        },
    )


@app.post(
    "/api/v1/research/evidence",
    response_model=EvidenceContractResponse,
    tags=["Evidence"],
    summary="Retrieve and normalize pharmacovigilance evidence",
)
def research_evidence(request: EvidenceRequest):
    """
    Run the research workflow for a drug name and return structured evidence contracts.

    - Retrieves adverse-event records from OpenFDA/FAERS (live external API).
    - Normalizes each record into a SharedEvidenceContract.
    - All results are labelled REVIEW_REQUIRED; human review is mandatory.
    - Does NOT establish causality, diagnose, or recommend treatment.

    Portal usage:
      Doctor, Researcher, Clinical Operations & Governance.
    """
    log_event("API_RESEARCH_EVIDENCE_REQUEST", report_id=request.report_id, drug=request.drug_name)

    report = {
        "report_id": request.report_id,
        "drug_name": request.drug_name,
    }

    workflow_result = run_research_workflow(report, limit=request.limit)

    # Build SharedEvidenceContract for each finding
    contracts = []
    for finding in workflow_result.get("findings", []):
        evidence_dict = finding.get("finding", {})
        contract = from_evidence_record(
            evidence_dict,
            validation_status="VALID",
            duplicate_status="UNKNOWN",
            conflict_status="UNKNOWN",
            human_review_status="PENDING",
            notes=(
                "Retrieved from OpenFDA/FAERS. "
                "FAERS records are spontaneous reports and do not establish causality."
            ),
        )
        contract_valid, contract_errors = contract.validate()
        if not contract_valid:
            contract.validation_status = "INVALID"
            contract.qc_errors = contract_errors
            contract.human_review_status = "PENDING"

        contracts.append(contract.to_dict())

    log_event(
        "API_RESEARCH_EVIDENCE_RESPONSE",
        report_id=request.report_id,
        status=workflow_result.get("status"),
        findings=len(contracts),
    )

    return EvidenceContractResponse(
        report_id=request.report_id,
        drug_name=request.drug_name,
        status=workflow_result.get("status", "UNKNOWN"),
        contract_version=CONTRACT_VERSION,
        findings_count=len(contracts),
        findings=contracts,
        uncertainty=workflow_result.get("uncertainty", {}),
        human_review=workflow_result.get("human_review", {}),
        service_disclaimer=(
            "These findings are from OpenFDA/FAERS adverse-event reports and are "
            "REVIEW_REQUIRED. They do not establish causality, constitute a clinical "
            "diagnosis, or represent treatment recommendations. Independent clinical "
            "review is mandatory before any clinical or regulatory use."
        ),
    )


@app.post(
    "/api/v1/qc/validate",
    response_model=QCValidateResponse,
    tags=["QC"],
    summary="Validate a record through the QC Engine (Shyamal boundary)",
)
def qc_validate(request: QCValidateRequest):
    """
    Validate a QC evidence record through Shyamal's QC Engine.

    When the QC engine package is not installed, returns SERVICE_BOUNDARY_NOT_MET
    with the exact blocker details. Never fabricates a pass result.

    Portal usage: Lab, Researcher, Manufacturing.
    """
    log_event("API_QC_VALIDATE_REQUEST")
    result = validate_qc_record(request.record)
    log_event("API_QC_VALIDATE_RESPONSE", qc_status=result["qc_status"])

    return QCValidateResponse(
        qc_status=result["qc_status"],
        qc_errors=result.get("qc_errors", []),
        engine_available=result["engine_available"],
        engine_version=result.get("engine_version"),
        blocker=result.get("blocker"),
    )


@app.get(
    "/api/v1/evidence/{evidence_id}",
    response_model=EvidenceGetResponse,
    tags=["Evidence"],
    summary="Retrieve a stored evidence record by ID",
)
def get_evidence(evidence_id: str):
    """
    Retrieve a previously stored evidence record by its evidence_id.

    Uses the flat-file evidence store (evidence_output.json).
    Returns 404 if not found.

    Portal usage: Doctor, Researcher, Clinical Operations & Governance.
    """
    if not evidence_id or not evidence_id.strip():
        raise HTTPException(status_code=400, detail="evidence_id must not be blank")

    records = load_evidence()
    for record in records:
        if isinstance(record, dict) and record.get("evidence_id") == evidence_id.strip():
            return EvidenceGetResponse(
                evidence_id=evidence_id,
                record=record,
                found=True,
                human_review_status="PENDING",
                disclaimer=(
                    "Evidence record retrieved from local store. "
                    "Human review is required before any clinical use."
                ),
            )

    raise HTTPException(
        status_code=404,
        detail=f"Evidence record '{evidence_id}' not found in local store.",
    )


@app.post(
    "/api/v1/patient/intake",
    response_model=PatientIntakeResponse,
    tags=["Patient Data"],
    summary="Ingest clinical patient observation with PII protection and QC validation",
)
def patient_intake(request: PatientIntakeRequest):
    """
    Ingest a clinical patient observation report.
    - Sanitizes and pseudonymizes direct patient identifiers (PII protection).
    - Normalizes into a SharedEvidenceContract.
    - Bridges record to Shyamal's QC Engine for Draft 2020-12 validation.
    - Persists into audit-backed evidence store.
    - Enforces mandatory human-review routing.
    """
    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    result = process_patient_intake(
        payload,
        store_evidence=request.store_evidence if request.store_evidence is not None else True,
    )
    if result["status"] == "REJECTED":
        raise HTTPException(status_code=400, detail={"errors": result["errors"]})

    return PatientIntakeResponse(
        status=result["status"],
        report_id=result["report_id"],
        pseudonymized_patient_id=result["pseudonymized_patient_id"],
        contract=result["contract"],
        qc_status=result.get("qc_status"),
        qc_result=result.get("qc_result"),
        stored=result["stored"],
        human_review_required=result["human_review_required"],
        service_disclaimer=result["service_disclaimer"],
    )


@app.get(
    "/api/v1/drug-safety/staged",
    tags=["Drug Safety"],
    summary="Retrieve staged Drug Safety records and validation status",
)
def drug_safety_staged():
    """
    Retrieve staged records from Shravani's Drug Safety workstream.
    Surfaces the exact validation status and provenance gap without fabricating data.
    """
    return get_staged_records()


@app.get(
    "/api/v1/discovery/candidates",
    tags=["Drug Discovery"],
    summary="Retrieve Drug Discovery candidate records with score reproducibility audit",
)
def discovery_candidates():
    """
    Retrieve candidate compounds from Shamit's Drug Discovery repository.
    Reports reproducibility of scores and missing score_inputs without fabricating values.
    """
    status = get_drug_discovery_status()
    raw_candidates = load_candidate_records()
    inspections = [inspect_candidate_record(c) for c in raw_candidates]
    return {
        "status": status["status"],
        "available": status["available"],
        "record_count": len(raw_candidates),
        "incomplete_score_count": status.get("incomplete_score_input_count", 0),
        "blocker": status.get("blocker"),
        "candidates": inspections,
    }


@app.post(
    "/api/v1/discovery/validate-candidate",
    tags=["Drug Discovery"],
    summary="Validate a Drug Discovery candidate record through Shyamal's Preclinical QC Engine",
)
def discovery_validate_candidate(candidate_record: Dict[str, Any]):
    """
    Bridge a candidate record into Shyamal's QC Engine (Draft 2020-12 Preclinical category).
    """
    if not isinstance(candidate_record, dict) or not candidate_record:
        raise HTTPException(status_code=400, detail="Candidate record must be a non-empty JSON object.")
    return validate_candidate_through_qc(candidate_record)


@app.get(
    "/api/v1/services/status",
    tags=["System"],
    summary="Return connected/disconnected service status for all integrations",
)
def services_status():
    """
    Return the verified status of all BHIV system integrations.

    Status values:
      VERIFIED — tested and confirmed working
      CONNECTED_WITH_KNOWN_BLOCKER — files present, dependency gap documented
      CONNECTED_WITH_LIMITATIONS — operational with identified missing score inputs
      PROPOSED — documented but no code or test
      BLOCKED — dependency unavailable
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "OpenFDA_FAERS": {
                "status": "VERIFIED",
                "note": "Live external API. Used by research_integration.py.",
                "url": "https://api.fda.gov/drug/event.json",
                "owner": "Jaydeep (canonical pipeline)",
            },
            "EvidenceStore": {
                "status": "VERIFIED",
                "note": "Flat-file JSON store (evidence_output.json). Local only.",
                "owner": "Jaydeep (canonical pipeline)",
            },
            "QCEngine_Shyamal": get_qc_engine_status(),
            "DrugSafety_Shravani": get_drug_safety_status(),
            "DrugDiscovery_Shamit": get_drug_discovery_status(),
            "PatientData_ClinicalIntake": get_patient_data_status(),
            "MASTERDB": {"status": "PROPOSED", "note": "Name referenced in documents. No endpoint, SDK or config found.", "owner": "Unknown"},
            "MDU": {"status": "PROPOSED", "note": "Name referenced in documents. No endpoint, SDK or config found.", "owner": "Unknown"},
            "Bucket": {"status": "PROPOSED", "note": "Name referenced in documents. No storage config found.", "owner": "Unknown"},
            "TANTRA_WorkflowExecutor": {"status": "PROPOSED", "note": "Name referenced. No API or execution trace found.", "owner": "Unknown"},
            "Parikshak": {"status": "PROPOSED", "note": "Name referenced. No endpoint found.", "owner": "Unknown"},
            "InsightFlow_Pravah": {"status": "PROPOSED", "note": "Name referenced. No API or SDK found.", "owner": "Unknown"},
            "KSML": {"status": "PROPOSED", "note": "Name referenced. No API or config found.", "owner": "Unknown"},
            "SETU": {"status": "PROPOSED", "note": "Name referenced. No API or config found.", "owner": "Unknown"},
            "Niyantran": {"status": "PROPOSED", "note": "Name referenced. No API or config found.", "owner": "Unknown"},
            "UniGuru_AgentFabric": {"status": "PROPOSED", "note": "Name referenced. No API, SDK or execution trace found.", "owner": "Unknown"},
        },
    }
