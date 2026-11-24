# BHIV BiotechSystem — Connected & Disconnected Service Verification
**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Date:** 2026-11-20 (EOD Assignment) · Audited: 2026-11-24

---

## 1. Classification Taxonomy

To prevent false claims of production readiness or architectural completion, every service is strictly classified into one of five states based on verifiable evidence:

- **VERIFIED:** Real endpoint or code exists, has been called or executed in test/runtime, and demonstrated reproducible pass results.
- **IMPLEMENTED / UNTESTED:** Local integration adapter/code written, but external dependency or cross-repository branch is unmerged or uninstalled in this environment.
- **PROPOSED:** Service or concept referenced in planning documents, but no actual endpoints, SDKs, configuration, or execution traces exist in the repository.
- **BLOCKED:** Dependency identified and inspected, but known defect, missing artifact, or schema incompatibility prevents working execution.
- **SIMULATED:** Mock or synthetic fallback only; no live system connection exists.

---

## 2. Comprehensive Service Audit Table

| Service / Subsystem | Canonical Name | Status | Evidence / Verification Method | Risk / Blocker | Responsible Owner | Next Action |
|---|---|---|---|---|---|---|
| **1. OpenFDA / FAERS** | Adverse Event Query API | **VERIFIED** | Live REST endpoint `https://api.fda.gov/drug/event.json`. Inspected in `openfda_connector.py`. 5 live tests passing. | Rate limits (240 req/min without key). Spontaneous reports only. | OpenFDA / Jaydeep | Add optional OpenFDA API key in `.env`. |
| **2. Evidence Store** | Local Flat-file Store | **VERIFIED** | Read/write in `evidence_output.json`. SHA-256 fingerprinting and conflict detection verified in `test_evidence_store.py`. | Concurrency limit: flat file cannot support high write volume. | Jaydeep / Hariom | Migrate to PostgreSQL/MASTERDB when available. |
| **3. QC Engine** | Preclinical Evidence QC | **IMPLEMENTED / UNTESTED** | Adapter `integration/qc_adapter.py`. Dynamic import check and Draft-2020-12 mapping implemented. Tested with mocked fallback. | Branch `feature/runtime-json-schema-validation` (PR #1) not merged into main. | Shyamal | Merge PR #1; publish package or add to shared dependencies. |
| **4. Drug Safety Import** | Biomedical Evidence Pipeline | **BLOCKED** | Adapter `integration/drug_safety_adapter.py`. Read-only check verified. | PR #1 unmerged. 10/10 staged producer records fail receiver validation due to missing `source_url` and provenance. | Shravani | Remediate producer payload in PR #1 to include provenance. |
| **5. Drug Discovery** | Candidate Scoring Engine | **PROPOSED** | Inspected `calculate_scores_v2.py`. Script requires `score.score_inputs` which is missing from candidate JSON. | Script crashes on committed inputs. Evidence cannot be fabricated. | Shamit | Provide valid candidate inputs matching `score.score_inputs` schema. |
| **6. MASTERDB** | Enterprise Clinical Database | **PROPOSED** | Grep of entire codebase found 0 connection strings, ORM models, or driver configurations. | System not configured or accessible. | System Architect | Provide database schema, connection driver, and test credentials. |
| **7. MDU** | Master Data Unit | **PROPOSED** | No endpoints, libraries, or schemas found in repository. | Architecture reference only. | Platform Team | Specify interface contract. |
| **8. Bucket** | Object Storage (S3/GCS) | **PROPOSED** | No cloud storage SDKs (boto3, google-cloud-storage) installed or configured. | Local disk only. | DevOps | Define S3/GCS bucket credentials and storage policy. |
| **9. TANTRA** | Workflow Executor | **PROPOSED** | Mentioned in notes; no executable workflow orchestrator files exist. | No execution traces. | Workflow Lead | Clarify orchestrator API and scheduling triggers. |
| **10. Parikshak** | Evaluation & Audit Engine | **PROPOSED** | No endpoint, script, or configuration found. | No code artifact. | QA Lead | Provide test runner or verification hook. |
| **11. InsightFlow / Pravah** | Streaming Analytics Engine | **PROPOSED** | No Kafka, RabbitMQ, or streaming consumer code found. | Unimplemented. | Data Engineering | Provide message bus broker URLs and schemas. |
| **12. KSML** | Biotech Knowledge Model | **PROPOSED** | No ontology parser or model files located. | Unimplemented. | Knowledge Lead | Supply ontology definitions and parsing utilities. |
| **13. SETU** | Integration Gateway | **PROPOSED** | No API gateway configuration (Kong, Envoy, NGINX) present in repo. | Unimplemented. | Infrastructure | Provide gateway ingress and routing rules. |
| **14. Niyantran** | Governance & Access Control | **PROPOSED** | No RBAC, ABAC, or token enforcement code located. | Unimplemented. | Security Lead | Provide IAM / OAuth2 provider specification. |
| **15. UniGuru / Agent Fabric** | AI Agent Framework | **PROPOSED** | No multi-agent runtime or execution logs found in codebase. | Unimplemented. | AI Research Lead | Define agent interaction protocol and tools. |

---

## 3. Immediate Action Plan for Technical Convergence

1. **QC Engine:** As soon as Shyamal merges PR #1, run:
   ```bash
   pip install -e ../bhiv-biotech-symmetrical-octo-invention
   pytest integration/test_hariom_integration.py -k TestValidQCRecord
   ```
2. **Drug Safety:** As soon as Shravani fixes the missing `source_url` and provenance in PR #1, merge and re-run:
   ```bash
   pytest integration/test_hariom_integration.py -k drug_safety
   ```
3. **Database Migration:** Replace `evidence_store.py` flat-file operations with an abstracted repository pattern ready for MASTERDB whenever connection parameters are released.
