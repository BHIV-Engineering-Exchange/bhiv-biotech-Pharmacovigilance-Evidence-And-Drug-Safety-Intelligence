# BHIV BiotechSystem — Connected & Disconnected Components

**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Date:** 25 November 2026  
**Audited By:** Antigravity Autonomous Integration Agent  

---

## 1. Classification Taxonomy

To prevent overstating production readiness, every service and component in the BHIV BiotechSystem is classified strictly based on empirical runtime evidence:

- **VERIFIED:** Endpoint or package exists, is installed or live, has been executed over real runtime or sockets, and passed reproducible tests.
- **CONNECTED_WITH_KNOWN_BLOCKER:** Code or staged files are present and integrated via adapters, but known upstream data defects (e.g., missing provenance) prevent full production ingestion. Data is preserved for human review without fabrication.
- **CONNECTED_WITH_LIMITATIONS:** Code or dataset is linked and operational, but specific non-blocking input gaps (e.g., missing candidate score inputs) exist and are documented without synthesizing values.
- **AVAILABLE:** In-process service module or adapter is implemented, verified with tests, and ready for deployment.
- **PROPOSED:** Architectural concept referenced in design documents or planning notes; no running endpoints, SDKs, or database configurations currently exist in the repository.
- **BLOCKED:** External dependency is required, but unmerged code or unavailable infrastructure blocks execution.

---

## 2. Comprehensive System Architecture & Component Status Matrix

| Component # | Canonical Name | Workstream / Role | Current Status | Integration Mechanism & Verification Evidence | Identified Risk or Blocker | Responsible Owner | Next Action |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **1** | **OpenFDA / FAERS Connector** | Clinical Pharmacovigilance Retrieval | **VERIFIED** | Live REST endpoint `https://api.fda.gov/drug/event.json`. Queried via `openfda_connector.py`. 5 live tests passing. | Public API rate limits (240 req/min). Spontaneous reports require clinical review. | Jaydeep / Hariom | Add optional commercial API key in `.env`. |
| **2** | **Evidence Store** | Local Flat-file Persistence | **VERIFIED** | Read/write in `evidence_output.json`. SHA-256 fingerprinting and conflict detection verified in `test_evidence_store.py`. | Concurrency bottleneck on multi-user writes. | Jaydeep / Hariom | Abstract repository pattern for PostgreSQL migration. |
| **3** | **QC Engine** | Preclinical & Biosimilarity QC | **VERIFIED** | Repository `bhiv-biotech-symmetrical-octo-invention`. Packaged via `pyproject.toml`, installed via `pip install -e`, verified with 32 automated tests and live Draft 2020-12 validation. | None for software execution. (Does not establish scientific validity). | Shyamal / Hariom | Merge `pyproject.toml` into upstream QC repo. |
| **4** | **Drug Safety Staging** | Biomedical Evidence Integration | **CONNECTED_WITH_KNOWN_BLOCKER** | Adapter `integration/drug_safety_adapter.py`. Staged receiver records loaded. 10/10 records fail receiver validation due to missing `source_url` and provenance. | Producer input data lacks required provenance. Data preserved for review. | Shravani | Re-run producer adapter with valid `source_url` and provenance. |
| **5** | **Drug Discovery** | Candidate Compound Scoring | **CONNECTED_WITH_LIMITATIONS** | Adapter `integration/drug_discovery_adapter.py`. Candidates loaded from `bhiv-discovery`. Inspection catches missing `score.score_inputs` without fabricating scores. | Candidate JSON lacks the 8 scoring dimensions. Scores not computed. | Shamit | Supply candidate records with valid `score_inputs`. |
| **6** | **Patient Data & Clinical Intake** | Clinical Adverse-Event Intake | **VERIFIED** | Adapter `integration/patient_data_adapter.py`. Ingests patient observations, pseudonymizes PII via SHA-256, validates via QC, and stores with audit trail. | Clinical reports require qualified physician review. | Hariom | Connect Doctor portal frontend to `/api/v1/patient/intake`. |
| **7** | **FastAPI Backend REST Service** | Core System Gateway | **VERIFIED** | `integration/api_service.py`. 9 endpoints tested via `TestClient` and real TCP socket Uvicorn server (`test_live_socket_server.py`). | Public deployment requires TLS ingress and OAuth2 tokens. | Hariom | Configure Dockerfile and uvicorn production daemon. |
| **8** | **MASTERDB** | Enterprise Clinical Database | **PROPOSED** | Codebase contains 0 connection strings, ORM models, or driver configurations. | System not configured or provisioned. | Platform / DevOps | Provision PostgreSQL instance and provide credentials. |
| **9** | **Bucket** | Cloud Object Storage (S3/GCS) | **PROPOSED** | No cloud storage SDKs (`boto3`, `google-cloud-storage`) installed or configured. | Local filesystem only. | Platform / DevOps | Provide S3/GCS bucket credentials and IAM policy. |
| **10** | **MDU** | Master Data Unit | **PROPOSED** | No endpoints, libraries, or schemas found in repository. | Architecture reference only. | Platform Team | Specify interface contract. |
| **11** | **TANTRA** | Workflow Executor | **PROPOSED** | Mentioned in notes; no executable workflow orchestrator files exist. | Unimplemented. | Workflow Lead | Clarify orchestrator API and scheduling triggers. |
| **12** | **Parikshak** | Evaluation & Audit Engine | **PROPOSED** | No endpoint, script, or configuration found. | No code artifact. | QA Lead | Provide test runner or verification hook. |
| **13** | **InsightFlow / Pravah**| Streaming Analytics Engine | **PROPOSED** | No Kafka, RabbitMQ, or streaming consumer code found. | Unimplemented. | Data Engineering | Provide message bus broker URLs and schemas. |
| **14** | **KSML** | Biotech Knowledge Model | **PROPOSED** | No ontology parser or model files located. | Unimplemented. | Knowledge Lead | Supply ontology definitions and parsing utilities. |
| **15** | **SETU / Niyantran** | API Gateway & IAM Access Control | **PROPOSED** | No API gateway (Kong, Envoy) or JWT/OAuth2 middleware present. | Endpoints lack token enforcement for public ingress. | Security Lead | Provide IAM / OAuth2 provider specification. |

---

## 3. Data Flow & Interface Architecture

```
                                [ CLINICAL / PORTAL INTAKE ]
                                             |
             +-------------------------------+-------------------------------+
             |                               |                               |
    [ Patient Observation ]         [ OpenFDA Drug Search ]         [ Drug Safety Staged ]
             |                               |                               |
    (SHA-256 Pseudonymize)           (FAERS Spontaneous)             (Prov. Gap Detection)
             |                               |                               |
             v                               v                               v
    +---------------------------------------------------------------------------------+
    |                     SharedEvidenceContract v1.0 (Canonical)                     |
    |  - evidence_id, source_record_id, source, source_url, drug_name, evidence_type  |
    |  - data_origin: REAL_WORLD | SYNTHETIC | TEST                                   |
    |  - validation_status: VALID | INVALID | REVIEW_REQUIRED                         |
    |  - human_review_status: PENDING | REVIEWED | CLOSED                             |
    |  - provenance: { source_system, underlying_dataset, retrieval_method }          |
    +---------------------------------------------------------------------------------+
                                             |
                                 build_qc_record_from_contract()
                                             |
                                             v
    +---------------------------------------------------------------------------------+
    |                 Shyamal Preclinical QC Engine (Draft 2020-12)                   |
    |  - 21 Required Fields Check                                                     |
    |  - Duplicate Detection (DUPLICATE_EVIDENCE_ID, DUPLICATE_STUDY_ID)              |
    |  - Conflict Detection (CONFLICTING_FIELD across same study_id)                  |
    |  - Evidence Quality Classification (VERIFIED, PARTIAL, CONFLICTING, etc.)       |
    |  - Human Review Requirement Enforcer (human_review_required: True)              |
    |  - Scientific Conclusion Guard (scientific_conclusion: None)                    |
    +---------------------------------------------------------------------------------+
                                             |
             +-------------------------------+-------------------------------+
             |                                                               |
             v                                                               v
   [ Local Flat-file Store ]                                        [ Doctor / Researcher API ]
   - evidence_output.json                                           - GET /health
   - SHA-256 Fingerprinting                                         - POST /api/v1/patient/intake
   - Audit Trail Appending                                          - POST /api/v1/qc/validate
   - Conflict Detection                                             - GET /api/v1/services/status
```
