# Biotech Gap Register

**Capability:** Pharmacovigilance Evidence and Drug Safety Intelligence Pipeline v1  
**Audit Date:** 2026-11-21  
**Current State:** 6 In-Repository Gaps Resolved; 1 P0 Cross-Capability Blocker; 3 Operational / Verification Items Tracked  

---

## 1. Master Gap Register

| ID | Capability / Domain | Gap Description | Technical Impact | Initial Evidence | Remediation & Current State | Owner | Priority | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **GAP-01** | Cross-Capability | Three of four candidate capability repositories are unavailable in workspace | Cannot audit cross-stream code, compare schemas, or build shared convergence pipeline | Clone contains only Pharmacovigilance codebase | Awaiting upstream access to Formulation/Stability, TB Discovery, and Biosimilarity QC repositories | Raj / Karan | P0 | **BLOCKED** |
| **GAP-02** | Architecture / Convergence | Cross-capability shared contract, versioning, and transport are undefined | Downstream consumers must guess envelope structures and error semantics | Local `EvidenceRecord` v1.1 schema implemented only | Candidate reference envelope defined (`EvidenceRecord` v1.1 with `data_origin`); ready for cross-team ratification | Raj / Karan | P0 | **OPEN** |
| **GAP-03** | Packaging / Dependency | Runtime dependencies were undeclared in a formal manifest | New environments could not deterministically reproduce environment | `openfda_connector.py` imports `requests`; no requirements file tracked | Added pinned `requirements.txt` (`requests>=2.31.0`, `pytest>=8.0.0`) and `pyproject.toml` | Karan | P1 | **RESOLVED** |
| **GAP-04** | Test Harness | Pytest discovery & temp directory permission locks in Windows sandboxes | Suite failed collection with missing paths or `PermissionError` on `tmp_path` | `pytest.ini` initially pointed to absent `tests/` and defaulted to locked user temp directory | Configured `testpaths = .` and `addopts = --basetemp=.pytest_tmp` in `pytest.ini`; ignored in `.gitignore` | Karan | P1 | **RESOLVED** |
| **GAP-05** | Evidence Schema | Synthetic vs. real-world evidence origin lacked explicit schema marker | Downstream consumers could mistake synthetic test fixtures for real clinical signals | `EvidenceRecord` had no explicit `data_origin` field | Added `data_origin` enum (`REAL_WORLD`, `SYNTHETIC`, `BENCHMARK`, `TEST`) to schema, normalizer, and store | Ansh / Pratik / Aman | P1 | **RESOLVED** |
| **GAP-06** | Evidence Schema | Validation lacked structural software-level field type checks | Malformed types could enter pipeline or incomplete payloads could pass validation | `validate_evidence` checked value presence and select enums only | Added type checks across all mandatory/optional fields, provenance dict keys, and allowed enum sets | Harsha / Ansh | P1 | **RESOLVED** |
| **GAP-07** | Evidence Storage | Conflicting payloads sharing a `source_record_id` were silently dropped | Content updates or conflicting reports under the same ID were dropped without audit trail | `_record_identity` keyed only on source ID; store skipped duplicates without content inspection | Implemented `detect_conflicts()` and `add_evidence_with_audit()`; logs `EVIDENCE_RECORD_CONFLICT` warnings | Aman / Pratik | P1 | **RESOLVED** |
| **GAP-08** | External Retrieval | Live OpenFDA API availability and error codes unverified in offline audit | Current real-world service reachability and query semantics remain unverified | Audit executed with mocked connector and offline error handling | Mocked test suite passes 100%; capture dated live smoke test when network access is enabled | Karan / Aman | P2 | **UNVERIFIED (OFFLINE)** |
| **GAP-09** | Evidence Store | Sample output data origin and reproducibility were unverified | Consumers could treat historic sample fixtures as newly observed live evidence | Committed `evidence_output.json` had no origin or provenance verification | Annotated all records in `evidence_output.json` with `"data_origin": "REAL_WORLD"`; verified against schema | Ansh / Pratik | P1 | **RESOLVED** |
| **GAP-10** | API Connector | Ingestion lacks automated pagination and rate-limit backoff | Search is restricted to single-page query (`limit` up to 100); bursting risks 429 errors | `openfda_connector.py` queries single page without exponential backoff retry loop | Connector is safe for current interactive CLI; add pagination generator and exponential backoff for batch ingestion | Karan | P2 | **OPEN** |

---

## 2. Priority Definition & Metrics

- **P0 (Critical Blocker):** Blocks convergence across capabilities or invalidates the core architecture.
- **P1 (High Priority):** Directly affects reproducibility, persistence integrity, and schema safety.
- **P2 (Operational / Quality):** External runtime verification, service reliability, and operational hardening.

### Gap Status Metrics:
- **Total Tracked Gaps:** 10
- **Resolved (Verified by Tests):** 6 (GAP-03, GAP-04, GAP-05, GAP-06, GAP-07, GAP-09)
- **External Dependency Blocked:** 1 (GAP-01)
- **Open / Architectural Candidate Ready:** 2 (GAP-02, GAP-10)
- **Operational Offline Verification:** 1 (GAP-08)
