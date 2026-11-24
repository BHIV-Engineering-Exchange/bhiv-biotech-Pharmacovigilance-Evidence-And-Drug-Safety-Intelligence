# BHIV BiotechSystem — Backend Architecture
**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Branch:** `feature/hariom-backend-integration-20261120`  
**Canonical repo:** `bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence`  
**Baseline commit:** `788a3e1a9242a3cdfeb7db0eaf08cd55ebcd5c15`  
**Date:** 2026-11-20 (EOD assignment) · Executed: 2026-11-24

---

## 1. System Overview

The BHIV BiotechSystem backend processes pharmacovigilance evidence through a deterministic pipeline:

```
Patient/Test Report
    ↓ validate_research_report()
Input Validation (research_integration.py)
    ↓ search_drug()
OpenFDA/FAERS Evidence Retrieval (openfda_connector.py)
    ↓ normalize_record()
Evidence Normalization (normalize_evidence.py)
    ↓ validate_evidence()
Schema Validation (evidence_schema.py)
    ↓ from_evidence_record()
Shared Evidence Contract (integration/shared_evidence_contract.py)  ← HARIOM NEW
    ↓ validate_qc_record()
QC Engine (integration/qc_adapter.py)  ← HARIOM ADAPTER [BLOCKED — PR not merged]
    ↓ add_evidence_with_audit()
Evidence Storage (evidence_store.py)
    ↓
Human Review Routing → human_review_status = "PENDING"
    ↓ FastAPI service
Researcher/Doctor-facing API (integration/api_service.py)  ← HARIOM NEW
```

---

## 2. Module Inventory

### Existing Canonical Modules (Jaydeep baseline — do not modify)

| Module | Purpose | Status |
|--------|---------|--------|
| `app.py` | CLI entry point — interactive drug search | VERIFIED |
| `src/openfda_connector.py` | OpenFDA/FAERS REST client | VERIFIED |
| `src/normalize_evidence.py` | Raw record → EvidenceRecord normalization | VERIFIED |
| `src/evidence_schema.py` | EvidenceRecord dataclass + validation | VERIFIED |
| `src/evidence_store.py` | Flat-file JSON persistence, duplicate/conflict detection | VERIFIED |
| `src/entity_resolution.py` | Deterministic drug entity resolution | VERIFIED |
| `src/research_integration.py` | Full research workflow with human-review routing | VERIFIED |
| `src/monitoring.py` | Structured pipeline logging | VERIFIED |
| `src/error_handler.py` | Application-level error boundary | VERIFIED |
| `src/__init__.py` | Path shim to expose root-level modules as `src.*` | VERIFIED |

### Hariom Integration Package (`integration/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `integration/__init__.py` | Package marker | NEW |
| `integration/shared_evidence_contract.py` | Versioned cross-workstream evidence contract | NEW |
| `integration/qc_adapter.py` | QC Engine service-boundary adapter (Shyamal) | NEW — UNTESTED |
| `integration/drug_safety_adapter.py` | Drug Safety read-only adapter (Shravani) | NEW — BLOCKED |
| `integration/api_service.py` | FastAPI REST service for Sarvesh's portals | NEW |
| `integration/test_hariom_integration.py` | 15-scenario integration test suite | NEW |

---

## 3. Data Flow & Schema Versions

| Schema | Version | Owner | Location |
|--------|---------|-------|----------|
| EvidenceRecord | 1.1 | Jaydeep | `src/evidence_schema.py` |
| SharedEvidenceContract | 1.0 | Hariom | `integration/shared_evidence_contract.py` |
| QC Evidence Schema | 1.0.0 | Shyamal | `schemas/evidence_qc_schema_v1.0.0.json` (separate repo) |
| Drug Safety Input | unversioned | Shravani | `integration_work/drug_safety_input.json` (PR #1) |
| Drug Discovery Records | unversioned | Shamit | `candidate_records_with_provenance.json` (separate repo) |

---

## 4. Storage Architecture

**Current:** Flat-file JSON store (`evidence_output.json`).  
- Duplicate detection: SHA-256 content fingerprint + source_record_id.  
- Conflict detection: Same source_record_id, different content fingerprint.  
- Conflict records: Logged to monitoring, NOT silently discarded, NOT auto-resolved.  

**Production requirement (not yet implemented):**  
- Database (MASTERDB — PROPOSED, no connection details available).  
- Authentication before evidence store access (BLOCKER — see BLOCKERS.md).

---

## 5. External Dependencies

| System | Type | Status |
|--------|------|--------|
| OpenFDA/FAERS API | Live REST | VERIFIED |
| QC Engine (Shyamal) | Python package import | BLOCKED — PR not merged |
| Drug Safety modules (Shravani) | File-based | BLOCKED — PR not merged |
| Drug Discovery scoring (Shamit) | File-based | PROPOSED — input structure undefined |
| MASTERDB | Unknown | PROPOSED — no connection details |
| TANTRA/Workflow | Unknown | PROPOSED — no connection details |

---

## 6. Startup

```bash
# 1. Clone and enter the canonical repository
git clone https://github.com/BHIV-Engineering-Exchange/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence
cd bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence

# 2. Check out Hariom integration branch
git checkout feature/hariom-backend-integration-20261120

# 3. Create virtual environment and install dependencies
python -m venv venv_hariom
venv_hariom\Scripts\activate          # Windows
# source venv_hariom/bin/activate     # Linux/macOS
pip install -r requirements.txt

# 4. Configure environment (optional — defaults work for local dev)
cp .env.example .env

# 5. Start the FastAPI service
uvicorn integration.api_service:app --host 0.0.0.0 --port 8000 --reload

# 6. Run all tests
pytest -v

# 7. Run Hariom integration tests only
pytest integration/test_hariom_integration.py -v
```

---

## 7. Disclaimer

This backend provides evidence retrieval and normalization support.  
It does **NOT** establish clinical safety, efficacy, causality, diagnosis or treatment recommendations.  
All findings are `REVIEW_REQUIRED` and require independent clinical review.
