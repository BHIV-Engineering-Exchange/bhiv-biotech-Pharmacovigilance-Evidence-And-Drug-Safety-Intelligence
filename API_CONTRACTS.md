# BHIV BiotechSystem — API Contracts & Reference
**Owner:** Hariom Upadhyay | Backend Architecture & Integration  
**Version:** `1.0.0` (Contract Version `1.0`)  
**Base URL:** `http://localhost:8000` (or configured gateway host)

---

## 1. Overview & Safety Mandate

This API serves pharmacovigilance and biomedical safety evidence for Sarvesh's seven frontend portals.
All responses follow strict medical safety boundaries:
- **No Causality Inference:** Adverse-event records represent reported statistical associations, not established clinical causality.
- **Mandatory Clinical Review:** Findings are tagged `REVIEW_REQUIRED` with `human_review.status = "PENDING"`.
- **Zero Patient PII:** Endpoints do not ingest or expose protected health information.

---

## 2. Endpoints Summary

| Method | Path | Summary | Target Portals | Status |
|---|---|---|---|---|
| `GET` | `/health` | System health & integration readiness | Operations, All Portals | **VERIFIED** |
| `POST` | `/api/v1/research/evidence` | Evidence retrieval, normalization & contract generation | Doctor, Researcher, Operations | **VERIFIED** |
| `POST` | `/api/v1/qc/validate` | QC validation boundary check | Lab, Researcher, Manufacturing | **VERIFIED** (Mock/Fallback boundary tested) |
| `GET` | `/api/v1/evidence/{evidence_id}` | Fetch stored evidence record | Doctor, Researcher, Operations | **VERIFIED** |
| `GET` | `/api/v1/services/status` | Real-time connection audit for all 10 BHIV services | Governance & Operations | **VERIFIED** |

---

## 3. Endpoint Specifications

### A. `GET /health`
Returns runtime status and component readiness.

#### Response (`200 OK`)
```json
{
  "status": "OK",
  "service": "BHIV Pharmacovigilance Backend API",
  "version": "1.0.0",
  "started_at": "2026-11-24T10:46:00.000000+00:00",
  "timestamp": "2026-11-24T10:55:00.000000+00:00",
  "pipeline_modules": {
    "openfda_connector": "AVAILABLE",
    "normalize_evidence": "AVAILABLE",
    "evidence_schema": "AVAILABLE",
    "evidence_store": "AVAILABLE",
    "entity_resolution": "AVAILABLE",
    "research_integration": "AVAILABLE",
    "monitoring": "AVAILABLE",
    "error_handler": "AVAILABLE"
  },
  "integrations": {
    "qc_engine_shyamal": "IMPLEMENTED / UNTESTED",
    "drug_safety_shravani": "BLOCKED",
    "drug_discovery_shamit": "PROPOSED",
    "fastapi": "AVAILABLE"
  }
}
```

---

### B. `POST /api/v1/research/evidence`
Retrieves adverse-event associations from OpenFDA, resolves drug entities, normalizes evidence, and constructs versioned `SharedEvidenceContract` objects.

#### Request Body
```json
{
  "report_id": "RPT-20261120-001",
  "drug_name": "aspirin",
  "limit": 5,
  "data_origin": "REAL_WORLD"
}
```

#### Response (`200 OK`)
```json
{
  "report_id": "RPT-20261120-001",
  "drug_name": "aspirin",
  "status": "REVIEW_REQUIRED",
  "contract_version": "1.0",
  "findings_count": 1,
  "findings": [
    {
      "evidence_id": "EV-10003304",
      "source_record_id": "10003304",
      "source": "OpenFDA/FAERS",
      "source_url": "https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:%22aspirin%22&limit=5",
      "drug_name": "ASPIRIN",
      "drug_identifier": "NDA020000",
      "adverse_event": "GASTRIC ULCER",
      "evidence_type": "FAERS adverse-event report",
      "event_date": null,
      "retrieved_at": "2026-11-24T10:55:00.000000+00:00",
      "schema_version": "1.1",
      "provenance": {
        "source_system": "OpenFDA",
        "underlying_dataset": "FAERS",
        "retrieval_method": "REST API",
        "transformation": "raw JSON -> normalized evidence",
        "source_record_id": "10003304"
      },
      "data_origin": "REAL_WORLD",
      "validation_status": "VALID",
      "duplicate_status": "UNIQUE",
      "conflict_status": "NO_CONFLICT",
      "human_review_status": "PENDING",
      "contract_version": "1.0",
      "entity_resolution_status": "MATCHED",
      "canonical_entity_name": "aspirin",
      "association_type": "REPORTED_ASSOCIATION",
      "notes": "Retrieved from OpenFDA/FAERS. FAERS records are spontaneous reports and do not establish causality."
    }
  ],
  "uncertainty": {
    "level": "MEDIUM",
    "limitations": [
      "FAERS records are spontaneous reports and do not establish causality.",
      "Absence of a record does not establish absence of risk.",
      "Entity resolution and data completeness may be incomplete."
    ],
    "missing_evidence": null
  },
  "human_review": {
    "required": true,
    "status": "PENDING",
    "role": "researcher or clinician"
  },
  "service_disclaimer": "These findings are from OpenFDA/FAERS adverse-event reports and are REVIEW_REQUIRED. They do not establish causality, constitute a clinical diagnosis, or represent treatment recommendations. Independent clinical review is mandatory before any clinical or regulatory use."
}
```

---

### C. `POST /api/v1/qc/validate`
Validates record against Shyamal's QC Engine specification.

#### Request Body
```json
{
  "record": {
    "schema_version": "1.0.0",
    "evidence_id": "QC-EV-001",
    "study_id": "STUDY-99",
    "source": "Preclinical Lab Alpha",
    "protocol_reference": "PROT-402",
    "sample_identification": "S-10",
    "control_identification": "CTRL-1",
    "experimental_conditions": "pH 7.4, 37C",
    "measurement_method": "HPLC",
    "method_validation_status": "VALIDATED",
    "raw_data_availability": "AVAILABLE",
    "missing_data": "NONE",
    "deviations": "NONE",
    "statistical_reporting": "ANOVA p<0.01",
    "reproducibility": "REPRODUCED_3X",
    "limitations": "In vitro only",
    "evidence_category": "Physicochemical",
    "synthetic_data_declaration": "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING",
    "reviewer_status": "NOT REVIEWED",
    "evidence_quality": "VERIFIED",
    "final_review_status": "OPEN"
  }
}
```

#### Response (`200 OK` — When QC engine unmerged in environment)
```json
{
  "qc_status": "SERVICE_BOUNDARY_NOT_MET",
  "qc_errors": [],
  "engine_available": false,
  "engine_version": null,
  "blocker": "QC Engine (Shyamal) is not installed in this environment. Import error: No module named 'qc_engine'. Required: pip install -e bhiv-biotech-symmetrical-octo-invention with branch feature/runtime-json-schema-validation checked out. Dependent PR: https://github.com/BHIV-Engineering-Exchange/bhiv-biotech-symmetrical-octo-invention/pull/1 (not merged)."
}
```

---

### D. `GET /api/v1/evidence/{evidence_id}`
Retrieves stored evidence from local flat store (`evidence_output.json`).

#### Response (`200 OK`)
```json
{
  "evidence_id": "EV-000001",
  "record": {
    "evidence_id": "EV-000001",
    "drug_name": "DOXYCYCLINE HYCLATE",
    "adverse_event": "Drug hypersensitivity",
    "source": "OpenFDA/FAERS",
    "source_record_id": "10003304",
    "schema_version": "1.1",
    "data_origin": "REAL_WORLD"
  },
  "found": true,
  "human_review_status": "PENDING",
  "disclaimer": "Evidence record retrieved from local store. Human review is required before any clinical use."
}
```

#### Response (`404 Not Found`)
```json
{
  "detail": "Evidence record 'EV-NONEXISTENT' not found in local store."
}
```

---

### E. `GET /api/v1/services/status`
Audit endpoint returning the factual connection state of all 10 BHIV services.

#### Response (`200 OK`)
```json
{
  "timestamp": "2026-11-24T10:55:00.000000+00:00",
  "services": {
    "OpenFDA_FAERS": { "status": "VERIFIED", "owner": "Jaydeep (canonical pipeline)" },
    "EvidenceStore": { "status": "VERIFIED", "owner": "Jaydeep (canonical pipeline)" },
    "QCEngine_Shyamal": { "status": "IMPLEMENTED / UNTESTED", "blocker": "QC engine PR not merged" },
    "DrugSafety_Shravani": { "status": "BLOCKED", "blocker": "10/10 records fail validation" },
    "DrugDiscovery_Shamit": { "status": "PROPOSED", "blocker": "score_inputs undefined" },
    "MASTERDB": { "status": "PROPOSED", "owner": "Unknown" },
    "MDU": { "status": "PROPOSED", "owner": "Unknown" },
    "Bucket": { "status": "PROPOSED", "owner": "Unknown" },
    "TANTRA_WorkflowExecutor": { "status": "PROPOSED", "owner": "Unknown" },
    "Parikshak": { "status": "PROPOSED", "owner": "Unknown" },
    "InsightFlow_Pravah": { "status": "PROPOSED", "owner": "Unknown" },
    "KSML": { "status": "PROPOSED", "owner": "Unknown" },
    "SETU": { "status": "PROPOSED", "owner": "Unknown" },
    "Niyantran": { "status": "PROPOSED", "owner": "Unknown" },
    "UniGuru_AgentFabric": { "status": "PROPOSED", "owner": "Unknown" }
  }
}
```
