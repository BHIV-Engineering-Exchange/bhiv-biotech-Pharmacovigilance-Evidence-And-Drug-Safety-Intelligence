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
- Checks dynamic availability of `qc_engine.engine.validate_record`.
- Maps `SharedEvidenceContract` to QC Engine's Draft-2020-12 schema (`schemas/evidence_qc_schema_v1.0.0.json`).
- Clearly tags unaligned QC fields (e.g. `protocol_reference`, `deviations`) as `NOT_REPORTED` rather than hallucinating scientific values.

### B. Drug Safety Adapter (`integration/drug_safety_adapter.py`)
- Reads staged outputs (`staged_receiver_records.json` / `drug_safety_input.json`) without mutating them.
- Identifies invalid records and isolates them under `PRESERVED_FOR_REVIEW` disposition.
- Surfaces upstream blocker: missing `source_url` and provenance in 10/10 producer records.

### C. Drug Discovery Boundary
- Inspection of `bhiv-biotech-drug-discovery` demonstrated that `calculate_scores_v2.py` fails on `candidate_records_with_provenance.json` due to missing `score.score_inputs`.
- In adherence to strict engineering rules, missing scores are **not fabricated**. The integration remains `PROPOSED` pending schema clarification from Shamit.

---

## 5. Verification Proof
- Canonical suite: **49 passed**.
- Hariom integration suite: **52 passed**.
- Total combined regression suite: **111 passed, 0 failed**.
- Test runtime: ~2.7 seconds.
