# BHIV BiotechSystem — Integration Architecture & Status
**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Branch:** `feature/hariom-backend-integration-20261120`  
**Baseline Commit:** `788a3e1a9242a3cdfeb7db0eaf08cd55ebcd5c15`  
**Date:** 2026-11-20 (EOD Assignment) · Verified: 2026-11-24

---

## 1. Executive Summary

This document describes the technical convergence architecture designed and implemented by Hariom Upadhyay to unify the BHIV BiotechSystem backend across all four contributor workstreams and prepare verified backend interfaces for Sarvesh's seven portals.

All implementation maintains the canonical baseline established by Jaydeep, respects strict component boundaries, avoids code-duplication across repositories, and accurately represents verified versus blocked integrations.

---

## 2. Workstream Convergence Matrix

| Workstream | Lead Owner | Repository | Branch / PR | Integration Mechanism | Status | Blocker / Dependency |
|---|---|---|---|---|---|---|
| **Pharmacovigilance & Biomedical Evidence** | Jaydeep / Hariom | `bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence` | `main` / `feature/hariom-backend-integration-20261120` | Native canonical pipeline | **VERIFIED** | Baseline fully functional. 49 regression tests passing. |
| **QC Engine** | Shyamal | `bhiv-biotech-symmetrical-octo-invention` | `feature/runtime-json-schema-validation` (PR #1) | Service boundary adapter (`integration/qc_adapter.py`) | **IMPLEMENTED / UNTESTED** | PR #1 not merged. QC package not installed in environment. Returns `SERVICE_BOUNDARY_NOT_MET`. |
| **Drug Safety / Staged Import** | Shravani | `bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence` | `drug-safety-evidence-integration` (PR #1) | Read-only adapter (`integration/drug_safety_adapter.py`) | **BLOCKED** | PR #1 not merged. 10/10 producer records missing `source_url` and provenance. Preserved for review. |
| **Drug Discovery** | Shamit | `bhiv-biotech-drug-discovery` | `main` | Documented contract gap | **PROPOSED** | `calculate_scores_v2.py` expects `score.score_inputs` not present in committed candidates. No adapter built. |

---

## 3. End-to-End Integrated Flow

```
[Patient / Doctor / Lab / Researcher Input]
                   │
                   ▼
       1. Request & Schema Validation
       (src/research_integration.py: validate_research_report)
                   │
                   ▼
       2. OpenFDA / FAERS Evidence Retrieval
       (src/openfda_connector.py: search_drug)
                   │
                   ▼
       3. Deterministic Entity Resolution & Normalization
       (src/entity_resolution.py & src/normalize_evidence.py)
                   │
                   ▼
       4. Shared Evidence Contract v1.0 Transformation
       (integration/shared_evidence_contract.py: from_evidence_record)
                   │
                   ├───► 5. Quality Control Boundary Adapter
                   │     (integration/qc_adapter.py: validate_qc_record)
                   │     - Real QC engine if installed
                   │     - SERVICE_BOUNDARY_NOT_MET if unmerged
                   │
                   ├───► 6. Duplicate & Conflict Detection / Audit Store
                   │     (src/evidence_store.py: add_evidence_with_audit)
                   │     - SHA-256 content fingerprinting
                   │     - Preserves conflicting records; logs alert
                   │
                   ▼
       7. Human Review Disposition & Uncertainty Quantification
       - status: REVIEW_REQUIRED
       - human_review: { required: True, status: PENDING }
                   │
                   ▼
       8. Secure FastAPI Output for Sarvesh Portals
       (integration/api_service.py)
```

---

## 4. Workstream Adapter Details

### A. QC Engine Adapter (`integration/qc_adapter.py`)
- Communicates across the boundary without copying Shyamal's code.
- Checks dynamic availability of `qc_engine.engine.validate_record` and `process_dataset`.
- Maps `SharedEvidenceContract` to QC Engine's Draft-2020-12 schema (`schemas/evidence_qc_schema_v1.0.0.json`, 21 required fields, `additionalProperties: false`).
- **Deterministic Field Formats & Enums:**
  - `deviations`: Formatted as JSON array (`list[str]`, defaulting to `[]`).
  - `missing_data`: Formatted as JSON array (`list[str]`, defaulting to `[]`).
  - `evidence_category`: Deterministically mapped (`"Clinical"` for FAERS reports and clinical observations; `"Preclinical"` for biosimilarity and candidate records; strict passthrough for analytical lab categories).
  - `evidence_quality`: Deterministically mapped (`"VERIFIED"` for VALID, `"INSUFFICIENT"` for INVALID, `"NEEDS REVIEW"` for REVIEW_REQUIRED/PENDING, `"CONFLICTING"` for CONFLICT).
  - `reviewer_status`: Deterministically mapped (`"NOT REVIEWED"` for PENDING/NOT_REQUIRED, `"IN REVIEW"` for IN_REVIEW, `"REVIEWED"` for REVIEWED, `"REQUIRES SECOND REVIEW"`, `"CLOSED"`).
  - `final_review_status`: Deterministically mapped (`"READY FOR HUMAN REVIEW"` for pending/review-required states).
  - `synthetic_data_declaration`: Deterministically mapped (`"SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING"` or `"REAL / SOURCE-VERIFIED"`).
  - Unaligned assay fields (`protocol_reference`, `sample_identification`, `control_identification`, `experimental_conditions`, `measurement_method`, `statistical_reporting`, `reproducibility`, `limitations`) default to `"NOT_REPORTED"` without fabricating scientific data.
  - Internal metadata keys (such as `_mapping_note`) are omitted by default and stripped during validation to comply with `additionalProperties: false`.
  - Non-destructive: original `SharedEvidenceContract` input dictionary is never mutated.
  - Direct local validation helper `validate_qc_schema_direct()` enables Draft 2020-12 schema validation independently of package installation.

### B. Drug Safety Adapter (`integration/drug_safety_adapter.py`)
- Reads staged outputs (`staged_receiver_records.json` / `drug_safety_input.json`) without mutating them.
- Identifies invalid records and isolates them under `PRESERVED_FOR_REVIEW` disposition.
- Surfaces upstream blocker: missing `source_url` and provenance in 10/10 producer records.

### C. Drug Discovery Boundary
- Inspection of `bhiv-biotech-drug-discovery` demonstrated that `calculate_scores_v2.py` fails on `candidate_records_with_provenance.json` due to missing `score.score_inputs`.
- In adherence to strict engineering rules, missing scores are **not fabricated**. The integration remains `PROPOSED` pending schema clarification from Shamit.

---

## 5. Verification Proof
- Canonical baseline suite: **49 passed**.
- Hariom integration test suite: **70 passed** (covering input validation, retrieval, error handling, QC schema Draft 2020-12 compliance, deduplication, conflict detection, entity resolution, provenance preservation, and API routes).
- Total combined regression suite: **119 passed, 0 failed**.
- Test runtime: ~9.4 seconds.
