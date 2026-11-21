# Biotech Dependency Register

**Capability:** Pharmacovigilance Evidence and Drug Safety Intelligence Pipeline v1  
**Last Audit / Verification:** 2026-11-21  
**Status:** In-Repository Dependencies Verified & Declared; Cross-Stream Dependencies Documented  

---

## 1. Master Dependency Register

| ID | From | To | Dependency Type | Dependency Description | Evidence & Current State | Owner | Status | Action Required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **DEP-01** | Shared Integration | Formulation & Stability capability | Cross-Stream Code | Source repository and Test 3 candidate submission | Absent from workspace; no code available for audit | Raj / Karan | **BLOCKED** | Obtain repository URL, commit hash, and executable instructions; audit independently. |
| **DEP-02** | Shared Integration | Drug Safety capability | Data Contract | Agreed cross-capability evidence contract & origin semantics | Local contract defined as `EvidenceRecord` v1.1 with explicit `data_origin` | Raj / Karan | **CANDIDATE READY** | Propose `EvidenceRecord` v1.1 as the reference adapter envelope for all 4 streams. |
| **DEP-03** | Shared Integration | TB Drug-Discovery capability | Cross-Stream Code | Source repository and Test 3 candidate submission | Absent from workspace; no code available for audit | Raj / Karan | **BLOCKED** | Obtain repository URL, commit hash, and executable instructions; audit independently. |
| **DEP-04** | Shared Integration | Biosimilarity & Preclinical QC | Cross-Stream Code | Source repository and Test 3 candidate submission | Absent from workspace; no code available for audit | Raj / Karan | **BLOCKED** | Obtain repository URL, commit hash, and executable instructions; audit independently. |
| **DEP-05** | CLI / Application | Python Environment & Runtime | Software Package | Python `>=3.10` runtime and `requests` HTTP library | `requests==2.32.5` installed; pinned in `requirements.txt` & `pyproject.toml` | Karan | **RESOLVED** | Maintained in repo manifest; reproducible across fresh virtual environments. |
| **DEP-06** | Retrieval Connector | OpenFDA Drug Event API | External Web API | Reachable endpoint `https://api.fda.gov/drug/event.json` | Mock test suite passes 100%; offline error boundary tested; live HTTP unverified | Karan / Aman | **UNVERIFIED (OFFLINE)** | Perform dated, logged live smoke test when network access is explicitly authorized. |
| **DEP-07** | Evidence Storage | Downstream Consumers | Data Integrity | Explicit data origin and non-destructive conflict policy | `data_origin` enum (`REAL_WORLD`, `SYNTHETIC`, `BENCHMARK`, `TEST`) and `detect_conflicts` implemented | Ansh / Pratik / Aman | **RESOLVED** | Propagate origin and conflict audit events (`EVIDENCE_RECORD_CONFLICT`) to consumers. |
| **DEP-08** | Root Modules | `src` Import Namespace | Code Architecture | Seamless resolution of `from src.* import ...` | Implemented via `src/__init__.py` path bridge; verified across all 53 test cases | Karan | **RESOLVED** | Maintain `src/__init__.py` to support both package and flat execution modes. |
| **DEP-09** | Test Harness | Pytest Temp Subsystem | Testing Infrastructure | Writable scratch directory for unit and integration fixtures | `addopts = --basetemp=.pytest_tmp` in `pytest.ini`; avoids Windows temp permission locks | Karan | **RESOLVED** | Preserved in repository configuration; ignored in `.gitignore`. |

---

## 2. Runtime & Development Dependency Manifest

The following software packages constitute the verified technical stack:

| Package | Role | Declared Requirement | Installed Version | License | Security & Integrity Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Python** | Runtime | `>=3.10` | `3.12.10` | PSF | Uses standard library (`dataclasses`, `json`, `hashlib`, `logging`, `re`, `datetime`). |
| **requests** | Runtime HTTP | `>=2.31.0` | `2.32.5` | Apache 2.0 | Used exclusively in `openfda_connector.py`. Configured with strict 30s timeout and exception wrappers. |
| **pytest** | Test Framework | `>=8.0.0` | `9.1.1` | MIT | Core test runner. Executed with `--basetemp=.pytest_tmp` for cross-platform sandboxing. |
| **pytest-asyncio** | Test Plugin | `>=0.23.0` | `1.4.0` | Apache 2.0 | Strict mode fixture execution. |
| **hypothesis** | Test Framework | `>=6.100.0` | `6.168.3` | MPL 2.0 | Property-based testing support. |

---

## 3. External API & Service Dependencies

| Service / Endpoint | Protocol | Auth | Rate Limits | Client Timeout | Failure Behavior |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **OpenFDA Drug Event API**<br>`https://api.fda.gov/drug/event.json` | HTTPS GET | None (Public Key optional) | 240 req/min (40 req/min unauthenticated) | 30 seconds | Handled via `openfda_connector.search_drug`: 404 returns `record_count: 0`; network failure returns `success: False` with descriptive error. |

---

## 4. Internal Module Dependency Graph

```
app.py (CLI entry point)
├── src.openfda_connector (search_drug)
│   └── requests
├── src.normalize_evidence (normalize_record)
│   ├── src.evidence_schema (EvidenceRecord, generate_evidence_id, ORIGIN_REAL_WORLD)
│   └── src.entity_resolution (EntityCandidate, resolve_entity)
├── src.evidence_schema (validate_evidence)
├── src.evidence_store (add_evidence, add_evidence_with_audit, detect_conflicts)
│   └── src.monitoring (log_event)
├── src.error_handler (handle_application_error, safe_error_message)
└── src.monitoring (log_event, get_logger)
```

Every internal dependency is verified locally through automated unit and integration tests.
