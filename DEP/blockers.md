# Daily Engineering Packet: Technical Blockers Register

**Project:** Pharmacovigilance Evidence and Drug Safety Intelligence Pipeline v1  
**Audit Date:** 2026-11-21  
**Status:** In-Repository Technical Blockers Resolved; Cross-Capability Dependencies Tracked  

---

## 1. Executive Summary

This document details all technical blockers and architectural gaps identified during the independent engineering audit of the Pharmacovigilance Evidence and Drug Safety Intelligence pipeline, the root-cause analysis, and the technical remediation implemented.

---

## 2. In-Repository Technical Blockers & Remediation

### Blocker 1: Missing Runtime & Development Dependency Manifest (GAP-03 / DEP-05)
- **Severity / Priority:** P1 (Integration / Reproducibility)
- **Status:** **RESOLVED**
- **Root Cause:** `openfda_connector.py` imported `requests` and tests required `pytest`, `pytest-asyncio`, and `hypothesis`, but neither `requirements.txt` nor `pyproject.toml` existed in the repository. A clean clone was not guaranteed to reproduce the environment.
- **Remediation:**
  - Created [requirements.txt](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/requirements.txt) with pinned runtime and testing dependencies (`requests>=2.31.0`, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `hypothesis>=6.100.0`).
  - Created [pyproject.toml](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/pyproject.toml) declaring project metadata, python requirement (`>=3.10`), runtime dependencies, and optional test dependencies.

---

### Blocker 2: Pytest Windows Temp Directory Permissions Failure (GAP-04)
- **Severity / Priority:** P1 (Test Execution)
- **Status:** **RESOLVED**
- **Root Cause:** On Windows restricted environments, `pytest` attempted to create temporary directories in `C:\Users\...\AppData\Local\Temp\pytest-of-...`, raising `PermissionError: [WinError 5] Access is denied` for any test using `tmp_path`.
- **Remediation:**
  - Configured `addopts = --basetemp=.pytest_tmp` in [pytest.ini](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/pytest.ini).
  - Added `.pytest_tmp/` to [.gitignore](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/.gitignore).

---

### Blocker 3: Lack of Explicit Evidence Origin Labeling (GAP-05 / DEP-07)
- **Severity / Priority:** P1 (Data Integrity / Audit Trail)
- **Status:** **RESOLVED**
- **Root Cause:** `EvidenceRecord` lacked an explicit data origin marker. Consumers could not reliably distinguish between synthetic benchmark records and real-world clinical/FAERS data.
- **Remediation:**
  - Added `data_origin` attribute to `EvidenceRecord` in [evidence_schema.py](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/evidence_schema.py) with validated origin domain: `{"REAL_WORLD", "SYNTHETIC", "BENCHMARK", "TEST"}` (defaulting to `"REAL_WORLD"`).
  - Added `data_origin` validation to `validate_evidence()`.
  - Added optional `data_origin` argument to `normalize_record()` in [normalize_evidence.py](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/normalize_evidence.py).
  - Updated sample store [evidence_output.json](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/evidence_output.json) to declare `"data_origin": "REAL_WORLD"`.

---

### Blocker 4: Incomplete Field Type Validation in Schema Boundary (GAP-06)
- **Severity / Priority:** P1 (Schema Integrity)
- **Status:** **RESOLVED**
- **Root Cause:** `validate_evidence` checked presence of select required fields and enum values, but did not enforce software-level type checks (e.g., non-string types could pass into string fields).
- **Remediation:**
  - Implemented comprehensive type checks across all mandatory string fields (`evidence_id`, `source`, `evidence_type`, `retrieved_at`, `source_url`, `schema_version`) and optional fields (`drug_name`, `adverse_event`, etc.) in [evidence_schema.py](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/evidence_schema.py).
  - Added type and completeness checks for all required provenance dictionary fields.
  - Added dedicated unit tests in [test_evidence_schema.py](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/test_evidence_schema.py).

---

### Blocker 5: Silent Dropping of Conflicting Payloads in Evidence Store (GAP-07 / DEP-07)
- **Severity / Priority:** P1 (Persistence & Audit Integrity)
- **Status:** **RESOLVED**
- **Root Cause:** `evidence_store.py` keyed identity solely on `source_record_id`. If an updated or conflicting payload arrived sharing the same `source_record_id` but with different adverse events or drug details, it was silently discarded as an exact duplicate without logging or alert.
- **Remediation:**
  - Implemented `detect_conflicts()` and `add_evidence_with_audit()` in [evidence_store.py](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/evidence_store.py).
  - Differentiated exact duplicate payloads (matching content fingerprint) from payload conflicts (same ID, divergent fingerprint).
  - Conflicts trigger warning events through `monitoring.log_event("EVIDENCE_RECORD_CONFLICT", ...)` and are tracked distinctly in audit results.
  - Added test coverage in [test_evidence_store.py](file:///c:/Users/sharc/OneDrive/Documents/BEE/Biotech/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/test_evidence_store.py).

---

## 3. External / Cross-Capability Blockers

| ID | Dependency | Description | Current Status | Resolution Path |
| :--- | :--- | :--- | :---: | :--- |
| **GAP-01** / **DEP-01,03,04** | Absent Capability Repositories | Formulation/Stability, TB Drug Discovery, and Biosimilarity QC repositories are not in this clone. | **BLOCKED** | Upstream coordination required to obtain repository access and execute separate audits. |
| **GAP-02** / **DEP-02** | Cross-Capability Contract | Shared multi-system schema and transport envelope not finalized. | **OPEN** | Propose candidate adapter boundary based on `EvidenceRecord` v1.1. |
| **GAP-08** / **DEP-06** | Live OpenFDA Service | Offline audit environment does not execute live network requests against FDA.gov. | **UNVERIFIED (OFFLINE)** | Mock testing verifies contract; live smoke test can be captured when live network is authorized. |

---

## 4. Verification

All fixes verified with the full automated test suite:
- **Command:** `pytest -v`
- **Result:** **53 passed in 0.69s** (100% pass rate)
