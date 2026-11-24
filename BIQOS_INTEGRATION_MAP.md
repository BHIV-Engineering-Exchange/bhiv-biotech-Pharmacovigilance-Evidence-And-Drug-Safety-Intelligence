# BHIV BiotechSystem — BIQOS Capability & Readiness Integration Map
**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Date:** 2026-11-20 (EOD Assignment) · Audited: 2026-11-24

---

## 1. BIQOS Capability Assessment Table

| Capability ID | Capability Name | Lead Owner | Repository & Branch | Runtime / Deployment Location | API / Schema Dependencies | Test Evidence | Actual Status | Critical Risks & Blockers | Next Immediate Action |
|---|---|---|---|---|---|---|---|---|---|
| **CAP-01** | OpenFDA Evidence Ingestion | Jaydeep / Hariom | `bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence` (`feature/hariom-backend-integration-20261120`) | Local runtime / container | OpenFDA REST API (`api.fda.gov`) | 49 baseline tests + 10 Phase 4 tests + 5 live API tests | **VERIFIED** | OpenFDA rate limiting; spontaneous reporting bias. | Add OpenFDA API key in `.env`. |
| **CAP-02** | Biomedical Evidence Normalization | Jaydeep / Hariom | Same (`src/normalize_evidence.py`, `src/evidence_schema.py`) | Python runtime | `EvidenceRecord` v1.1 | Normalization unit tests passed (100%) | **VERIFIED** | Entity resolution ambiguous for brand variations. | Maintain conservative `UNRESOLVED` fallback. |
| **CAP-03** | Shared Evidence Contract | Hariom Upadhyay | Same (`integration/shared_evidence_contract.py`) | Python runtime / FastAPI | `SharedEvidenceContract` v1.0 | 52 integration tests passed (100%) | **VERIFIED** | Cross-workstream adoption pending PR reviews. | Review and merge branch into canonical main. |
| **CAP-04** | REST Service Gateway | Hariom Upadhyay | Same (`integration/api_service.py`) | FastAPI on `0.0.0.0:8000` | Pydantic v2 / OpenAPI 3.1 | TestClient HTTP tests passed | **VERIFIED** | Authentication not yet enforced. | Add OAuth2/JWT middleware pre-staging. |
| **CAP-05** | Preclinical Evidence QC | Shyamal | `bhiv-biotech-symmetrical-octo-invention` (`feature/runtime-json-schema-validation`) | Python import boundary | Draft 2020-12 JSON Schema v1.0.0 | Adapter boundary tests passed with fallback | **IMPLEMENTED / UNTESTED** | PR #1 unmerged; package uninstalled. | Shyamal to merge PR #1; Hariom to run end-to-end test. |
| **CAP-06** | Biomedical Safety Staged Import | Shravani | `bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence` (`drug-safety-evidence-integration`) | Read-only adapter | Staged receiver JSON | Adapter reports 10/10 invalid records preserved | **BLOCKED** | Missing `source_url` & provenance; PR unmerged. | Shravani to fix input data in PR #1. |
| **CAP-07** | Candidate Evidence Scoring | Shamit | `bhiv-biotech-drug-discovery` (`main`) | Python CLI | `calculate_scores_v2.py` | Documented schema incompatibility | **PROPOSED** | Script crashes on committed candidate records. | Shamit to define and provide `score_inputs`. |
| **CAP-08** | Audit Trail & Conflict Store | Jaydeep / Hariom | Canonical repo (`src/evidence_store.py`) | Flat file JSON (`evidence_output.json`) | SHA-256 fingerprinting | 6 conflict & deduplication tests passed | **VERIFIED** | File locking at high concurrency. | Migrate to MASTERDB (PostgreSQL). |
| **CAP-09** | Enterprise Database (MASTERDB) | Platform Team | N/A | Not deployed | SQL / ORM | No tests; no connection string | **PROPOSED** | Database not provisioned. | Provision PostgreSQL instance. |
| **CAP-10** | Portal Integration Gateway | Sarvesh / Hariom | Integration API | FastAPI REST endpoints | OpenAPI contract | 5 API contract tests passed | **VERIFIED** | Frontend client integration in progress. | Sarvesh to bind frontend views to endpoints. |

---

## 2. Deployment Prerequisites Checklist

Before promoting this backend to staging or cloud environments:

- [x] **Branch Isolation:** Working on `feature/hariom-backend-integration-20261120`; canonical `main` preserved.
- [x] **Automated Regression:** 111/111 automated tests passing locally.
- [x] **Safe Error Handling:** Application-level error boundary intercepts unexpected faults without crash.
- [x] **Contract Validation:** Explicit enum and type validation enforced at input and output boundaries.
- [ ] **Authentication Layer:** OAuth2 bearer token validation must be enabled for all non-health routes.
- [ ] **Database Provisioning:** PostgreSQL database provisioned to replace `evidence_output.json`.
- [ ] **Ingress & TLS:** HTTPS reverse proxy (NGINX / Cloudflare) configured with TLS certificates.
- [ ] **Upstream Merges:** Shyamal PR #1 and Shravani PR #1 merged.
