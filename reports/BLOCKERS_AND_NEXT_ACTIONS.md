# BHIV BiotechSystem — Integration Blockers, Technical Debt & Action Handover Register

**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Date:** 25 November 2026  
**Auditor / Integration Agent:** Antigravity Autonomous Integration Agent  
**Status:** Active Handover Document  

---

## 1. Blocker Executive Summary & Status Matrix

| Blocker ID | Severity | Impacted Workstream | Responsible Owner | Convergence Status | Operational Impact |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **BLK-001** | HIGH | Drug Safety / Biomedical Evidence | Shravani | **ACTIVE / MITIGATED** | Staged records lack provenance & `source_url`; isolated under review without data loss. |
| **BLK-002** | HIGH | QC Engine Packaging Reproducibility | Shyamal | **RESOLVED BY HARIOM** | PEP 621 `pyproject.toml` implemented; clean `pip install -e .` operational. |
| **BLK-003** | MEDIUM | Drug Discovery Candidate Scoring | Shamit | **ACTIVE / MITIGATED** | Candidate records lack `score.score_inputs`; audited & bridged without score hallucination. |
| **BLK-004** | LOW (POC) / HIGH (PROD) | Core Persistence Infrastructure | DevOps / Platform | **DOCUMENTED** | Flat JSON store operational for POC; PostgreSQL (MASTERDB) & S3 required for staging. |
| **BLK-005** | HIGH (PROD) | IAM / API Token Middleware | Security / Hariom | **DOCUMENTED** | Endpoints open for local evaluation; OAuth2/JWT middleware required before public ingress. |

---

## 2. Detailed Blocker Analysis & Remediation Plans

### BLK-001: Shravani Staged Producer Records Fail Receiver Validation
- **Severity:** HIGH / WORKSTREAM BOUNDARY
- **Impacted Subsystem:** Drug Safety & Biomedical Evidence Pipeline (`integration_work/staged_receiver_records.json`)
- **Root Cause Analysis:**
  All 10 staged records produced by Shravani's export adapter on branch `drug-safety-evidence-integration` fail receiver schema validation:
  1. `source_url` is an empty string (`""`) rather than a valid URL or URI reference.
  2. The mandatory `provenance` dictionary lacks required sub-fields: `source_system`, `underlying_dataset`, `retrieval_method`, and `transformation`.
  3. The upstream source artifact (`existing_test1_csv`) was not committed to the repository, preventing automated regeneration.
- **Hariom Integration Mitigation:**
  - Implemented `integration/drug_safety_adapter.py`.
  - Staged records are loaded safely, analyzed deterministically, and preserved verbatim under `PRESERVED_FOR_REVIEW`.
  - Zero records discarded, zero records altered, zero synthetic provenance hallucinated.
  - Exposed via endpoint `GET /api/v1/drug-safety/staged` and testable via `validate_drug_safety_through_qc()`.
- **Action Item for Shravani:**
  1. Update `drug_safety_import_adapter.py` to populate valid `source_url` (e.g., `https://api.fda.gov/drug/event.json?...` or `internal://drug-safety/test1`).
  2. Populate `provenance` dictionary matching `SharedEvidenceContract` specification:
     ```python
     "provenance": {
         "source_system": "OpenFDA_FAERS",
         "underlying_dataset": "faers_q3_2026",
         "retrieval_method": "REST_API_BATCH",
         "transformation": "NORMALIZED_TO_EVIDENCE_V1"
     }
     ```
  3. Re-export `integration_work/staged_receiver_records.json` and push to upstream branch.

---

### BLK-002: Shyamal QC Engine Packaging & Clone Reproducibility [RESOLVED]
- **Severity:** HIGH / INTEGRATION RUNTIME BOUNDARY (Formerly Critical Blocker)
- **Impacted Subsystem:** QC Engine (`bhiv-biotech-symmetrical-octo-invention`)
- **Root Cause Analysis:**
  While Shyamal merged PR #1 (`3151e482bb6c39f11c725944f72aa2824dc549c6`) containing 32 passing tests and Draft 2020-12 schemas, the repository lacked any build manifest (`pyproject.toml` or `setup.py`). Consequently:
  - Running `pip install -e .` or `pip install .` failed immediately with `ERROR: File "setup.py" or "setup.cfg/pyproject.toml" not found`.
  - The runtime required manual `.pth` symlink hacks (`bhiv_qc.pth`), which breaks container builds, CI pipelines, and multi-developer onboarding.
- **Hariom Integration Resolution:**
  - Authored standard PEP 621 packaging manifest at `bhiv-qc/pyproject.toml`:
    - Declared `build-system` using `setuptools>=61.0`.
    - Declared package metadata (`name = "qc-engine"`, `version = "1.0.0"`).
    - Configured automatic package discovery for `bhiv_qc`.
    - Declared package data inclusion for `bhiv_qc.schemas: *.json` and `bhiv_qc.data: *.json`.
  - Executed clean installation: `pip install -e C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-qc --no-deps`.
  - Removed `bhiv_qc.pth` workaround. Verified live execution of all 32 QC tests and cross-repo validation without path overrides.
- **Action Item for Shyamal:**
  - Merge the authored `pyproject.toml` into `bhiv-biotech-symmetrical-octo-invention` `main` branch to guarantee reproducibility across all developer clones and Docker builds.

---

### BLK-003: Shamit Drug Discovery Candidate Records Schema Mismatch
- **Severity:** MEDIUM / SCIENTIFIC REPRODUCIBILITY
- **Impacted Subsystem:** Drug Discovery Pipeline (`bhiv-biotech-drug-discovery`)
- **Root Cause Analysis:**
  The scoring pipeline script `calculate_scores_v2.py` requires compound records to contain a nested `score.score_inputs` dictionary with 8 quantitative parameters (e.g., binding affinity, molecular weight, lipophilicity, bioavailability).
  However, all 10 records in `candidate_records_with_provenance.json` lack `score.score_inputs` entirely. Running the scoring script directly throws a `KeyError: 'score_inputs'` or produces `NaN` outputs.
- **Hariom Integration Mitigation:**
  - Implemented `integration/drug_discovery_adapter.py`.
  - Inspects all 10 candidate compounds and validates scoring completeness.
  - Categorizes incomplete records with `score_status: "INCOMPLETE"` and flags `human_review_required: True`.
  - Bridges candidates into `SharedEvidenceContract` and validates them against Shyamal's Preclinical QC schema.
  - In strict compliance with scientific integrity rules, scores have **not** been synthesized or hallucinated.
- **Action Item for Shamit:**
  1. Update candidate compound exporter to include `score.score_inputs` with verified assay/docking data:
     ```json
     "score": {
         "score_inputs": {
             "binding_affinity_kd_nm": 14.2,
             "molecular_weight": 382.4,
             "logp": 2.8,
             "tpsa": 64.5,
             "rotatable_bonds": 5,
             "h_bond_donors": 2,
             "h_bond_acceptors": 4,
             "solubility_ug_ml": 85.0
         }
     }
     ```
  2. Alternatively, update `calculate_scores_v2.py` to allow default placeholder weights with explicit uncertainty flags.

---

### BLK-004: Persistent Relational Database (MASTERDB) & Object Storage Provisioning
- **Severity:** LOW FOR POC / CRITICAL FOR STAGING & PRODUCTION
- **Impacted Subsystem:** Core Backend Storage & Scalability
- **Root Cause Analysis:**
  Evidence records, audit logs, and deduplication states currently persist to local filesystem files (`evidence_output.json`, `audit_trail.log`). While this provides atomic, reliable, and testable operation for local verification (155 tests passing), concurrent multi-user environments (Doctor, Lab, Research portals) will face file-locking contention.
- **Hariom Integration Architecture:**
  - Built-in thread-safe / process-safe file handling with SHA-256 deduplication and conflict detection.
  - Storage interface abstraction prepared in `evidence_store.py`.
- **Action Item for DevOps / Platform Lead:**
  1. Provision managed PostgreSQL 16 database (MASTERDB) and provide `DATABASE_URL` in `.env`.
  2. Provision S3-compatible object storage bucket (`bhiv-evidence-vault`) for raw PDF/genomic raw artifacts and provide credentials in `.env`.
  3. Hariom team will plug in SQLAlchemy / asyncpg driver into the existing storage repository pattern.

---

### BLK-005: Absence of Authentication & Access Control (IAM / RBAC)
- **Severity:** HIGH FOR PRODUCTION INGRESS / ACCEPTABLE FOR LOCAL VERIFICATION
- **Impacted Subsystem:** Security, Governance & Compliance
- **Root Cause Analysis:**
  The current FastAPI endpoints at `/api/v1/*` do not enforce bearer token authentication or role-based authorization scopes (e.g., `doctor:read`, `lab:write`, `researcher:all`).
- **Hariom Integration Architecture:**
  - Rigorous PII protection implemented on patient ingestion endpoints (`integration/patient_data_adapter.py`), rejecting direct identifiers (SSN, passport, full names) and applying deterministic SHA-256 pseudonymization.
  - Service structure supports FastAPI dependency injection (`Depends(get_current_user)`).
- **Action Item for Security Team & Hariom:**
  1. Integrate OAuth2/OIDC JWT validation middleware in `integration/api_service.py`.
  2. Define role scopes corresponding to user portals:
     - `SCOPE_CLINICAL_INTAKE` -> `/api/v1/patient/intake`
     - `SCOPE_QC_OPERATIONS` -> `/api/v1/qc/validate`
     - `SCOPE_RESEARCH_ANALYSIS` -> `/api/v1/research/evidence`, `/api/v1/discovery/*`

---

## 3. Team Handover Action Items & Responsibilities

```
+-----------------------------------------------------------------------------------------+
|                                BHIV BIOTECHSYSTEM HANDOVER                             |
+-------------------+--------------------------------------------+------------------------+
| Recipient         | Deliverable / Responsibility               | Timeline               |
+-------------------+--------------------------------------------+------------------------+
| Shravani          | BLK-001: Fix Drug Safety provenance & URL  | Sprint 2 Day 1         |
| Shyamal           | BLK-002: Merge pyproject.toml to upstream  | Immediate              |
| Shamit            | BLK-003: Provide score.score_inputs data   | Sprint 2 Day 1         |
| DevOps / Platform | BLK-004: Provision PostgreSQL & S3 bucket  | Pre-Staging Deployment |
| Security Architect| BLK-005: Provide OAuth2/OIDC Token Specs   | Pre-Staging Deployment |
| Hariom Upadhyay   | Core Backend & Integration Ownership       | Handed Over (95%)      |
+-------------------+--------------------------------------------+------------------------+
```

---

## 4. Verification Checklists for Next Engineering Sprint

1. **When Shravani updates Drug Safety export:**
   ```bash
   python -c "from integration.drug_safety_adapter import DrugSafetyAdapter; a = DrugSafetyAdapter(); print(a.load_and_validate_staged_records())"
   ```
   *Expected:* Validation failures drop from 10 to 0.

2. **When Shamit updates Drug Discovery candidate records:**
   ```bash
   python -c "from integration.drug_discovery_adapter import DrugDiscoveryAdapter; a = DrugDiscoveryAdapter(); print(a.inspect_candidates())"
   ```
   *Expected:* `candidates_with_score_inputs` increases from 0 to 10.

3. **When PostgreSQL is connected:**
   - Update `DATABASE_URL` in `.env`.
   - Run `pytest tests/test_database_persistence.py`.
