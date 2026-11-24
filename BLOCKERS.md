# BHIV BiotechSystem — Blockers, Dependencies & Remediation Register
**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Date:** 2026-11-20 (EOD Assignment) · Audited: 2026-11-24

---

## 1. Active Technical Blockers

### BLK-001: Shravani Staged Producer Records Fail Receiver Validation
- **Severity:** HIGH / WORKSTREAM BLOCKER
- **Impacted Workstream:** Drug Safety / Biomedical Evidence Integration
- **Root Cause:** All 10 records in `integration_work/staged_receiver_records.json` on branch `drug-safety-evidence-integration` fail receiver validation because `source_url` is empty string and mandatory provenance fields (`source_system`, `underlying_dataset`, `retrieval_method`, `transformation`) are missing. The original `existing_test1_csv` source artifact was not found in the repository.
- **Handling in Hariom Integration:** `integration/drug_safety_adapter.py` isolates failed records, preserves them verbatim under `PRESERVED_FOR_REVIEW`, and reports exact failure count without discarding or altering data.
- **Responsible Owner:** Shravani
- **Required Action:** Update producer adapter in PR #1 to populate valid `source_url` and provenance dictionary before merging into `main`.

---

### BLK-002: Shyamal QC Engine Feature Branch Unmerged
- **Severity:** MEDIUM / INTEGRATION BOUNDARY
- **Impacted Workstream:** QC Engine (`bhiv-biotech-symmetrical-octo-invention`)
- **Root Cause:** Branch `feature/runtime-json-schema-validation` (PR #1) is 7 commits ahead and 2 commits behind `main`. Package is not published or installed in the canonical repository environment.
- **Handling in Hariom Integration:** `integration/qc_adapter.py` provides a safe dynamic import boundary. When the engine is uninstalled, it gracefully outputs `SERVICE_BOUNDARY_NOT_MET` with detailed diagnostic instructions rather than raising an uncaught exception or faking validation.
- **Responsible Owner:** Shyamal
- **Required Action:** Rebase and merge PR #1 on `bhiv-biotech-symmetrical-octo-invention`, tag release v1.0.0, or publish wheel.

---

### BLK-003: Shamit Drug Discovery Candidate Records Schema Mismatch
- **Severity:** MEDIUM / EVIDENCE REPRODUCIBILITY
- **Impacted Workstream:** Drug Discovery (`bhiv-biotech-drug-discovery`)
- **Root Cause:** `calculate_scores_v2.py` requires records to possess a nested `score.score_inputs` dictionary. However, all 10 records in `candidate_records_with_provenance.json` lack this structure, causing scoring crashes.
- **Handling in Hariom Integration:** Documented in `CONNECTED_SERVICES.md` as `PROPOSED`. In accordance with scientific integrity rules, scores have **not** been hallucinated or synthesized.
- **Responsible Owner:** Shamit
- **Required Action:** Provide candidate records containing valid `score_inputs` or update scoring script to gracefully handle default weights.

---

### BLK-004: Lack of Persistent Database (MASTERDB) & Object Store (Bucket)
- **Severity:** LOW FOR POC / CRITICAL FOR PRODUCTION
- **Impacted Workstream:** Core Backend Persistence
- **Root Cause:** Current evidence store operates via a single flat JSON file (`evidence_output.json`). While concurrent conflict detection and SHA-256 deduplication work for local testing, multi-user portals will encounter file locking and scale bottlenecks.
- **Handling in Hariom Integration:** Flat store maintained with atomic reads/writes and audit logging.
- **Responsible Owner:** Platform / DevOps Lead
- **Required Action:** Provision PostgreSQL instance (MASTERDB) and S3/GCS bucket; provide connection string in `.env`.

---

### BLK-005: Absence of Authentication & Access Control (Niyantran / IAM)
- **Severity:** HIGH FOR PRODUCTION DEPLOYMENT
- **Impacted Workstream:** Security & Governance
- **Root Cause:** The FastAPI service endpoints currently do not enforce JWT/OAuth2 bearer tokens or role-based access control (RBAC).
- **Handling in Hariom Integration:** Sensitive operations restricted; endpoints do not expose patient PII.
- **Responsible Owner:** Security Architect / Hariom
- **Required Action:** Implement OAuth2 / OIDC token middleware at `/api/v1/*` before exposing endpoints to public ingress.

---

## 2. Summary Action Matrix

| Blocker ID | Owner | Action Item | Target Delivery |
|---|---|---|---|
| **BLK-001** | Shravani | Fix provenance & source_url in `drug_safety_import_adapter.py` | Next Sprint Cycle |
| **BLK-002** | Shyamal | Merge PR #1 and provide installable package | Immediate |
| **BLK-003** | Shamit | Align `candidate_records_with_provenance.json` with scoring script | Next Sprint Cycle |
| **BLK-004** | DevOps | Provision MASTERDB & S3 bucket | Pre-Staging |
| **BLK-005** | Security | Provide JWT authentication specification | Pre-Staging |
