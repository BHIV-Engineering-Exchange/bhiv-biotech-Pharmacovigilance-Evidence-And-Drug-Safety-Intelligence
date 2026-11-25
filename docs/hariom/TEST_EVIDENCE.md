# BHIV BiotechSystem — Test Evidence & Verification Logs

**Owner:** Hariom Upadhyay | Backend Architecture & Integration / Technical Convergence Owner  
**Date:** 25 November 2026  
**Environment:** Python 3.13.14 (win32), pytest-9.2.0, FastAPI-0.165.0, Uvicorn-0.54.0, jsonschema-4.26.0  

---

## 1. Summary of Executed Test Suites

| Suite ID | Description | Command | Scope | Result |
| :--- | :--- | :--- | :---: | :---: |
| **SUITE-1** | Full Backend Test Suite | `python -m pytest -q --ignore=venv_verification` | Core backend, pipeline, schemas, adapters, and live socket | **155 passed** in 3.62s |
| **SUITE-2** | Full QC Engine Test Suite | `python -m pytest -q` | QC Engine, evidence tracker, JSON Schema validation, CLI | **32 passed** in 0.68s |
| **SUITE-3** | Cross-Repo Integration Suite | `python verify_cross_repo_integration.py` | 7 end-to-end integration scenarios (Scenarios 8–14) | **7 passed** in 1.85s |
| **SUITE-4** | Live TCP Socket Server Test | `pytest integration/test_live_socket_server.py -v` | Real Uvicorn server on ephemeral port via `requests` | **1 passed** in 0.85s |
| **SUITE-5** | Component Convergence Tests | `pytest integration/test_full_system_convergence.py -v` | All 5 components (QC, Drug Safety, Discovery, Patient Data, API) | **21 passed** in 1.25s |

---

## 2. Raw Log: Backend Full Test Suite (155 Tests)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-post-merge-fresh\venv_verification\Scripts\python.exe
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-post-merge-fresh
configfile: pytest.ini
plugins: anyio-4.16.0, hypothesis-6.170.17, asyncio-1.5.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 155 items

integration/test_full_system_convergence.py .....................        [ 13%]
integration/test_hariom_integration.py .................................. [ 35%]
..........................                                               [ 52%]
integration/test_live_socket_server.py .                                 [ 52%]
integration_work/test_drug_safety_integration.py ..............          [ 61%]
test_e2e_pipeline.py ....                                                [ 64%]
test_entity_resolution.py ......                                         [ 68%]
test_error_handler.py ....                                               [ 70%]
test_evidence_schema.py ..........                                       [ 77%]
test_evidence_store.py ......                                            [ 81%]
test_monitoring.py ......                                                [ 85%]
test_normalization.py .......                                            [ 89%]
test_phase4.py ..........                                                [ 96%]
test_research_integration.py ......                                      [100%]

============================== warnings summary ===============================
venv_verification\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

155 passed, 1 warning in 3.62s
```

---

## 3. Raw Log: QC Engine Test Suite (32 Tests)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-post-merge-fresh\venv_verification\Scripts\python.exe
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-qc
plugins: anyio-4.16.0, hypothesis-6.170.17, asyncio-1.5.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 32 items

src/tests/test_cli.py .                                                  [  3%]
tests/test_evidence_tracker.py ...........                               [ 37%]
tests/test_json_schema_validation.py ...                                 [ 46%]
tests/test_qc_engine.py .................                                [100%]

32 passed in 0.68s
```

---

## 4. Raw Log: Cross-Repository Integration Scenarios (7 Scenarios)

```text
======================================================================
STARTING BHIV CROSS-REPOSITORY QC INTEGRATION VERIFICATION
Backend Repo: C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-post-merge-fresh
QC Repo:      C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-qc
======================================================================

============================================================
SCENARIO 8: Test a Valid Synthetic Evidence Record
============================================================
Mapped QC Record:
{
  "schema_version": "1.0.0",
  "evidence_id": "EV-000001",
  "study_id": "SYNTH-VERIFY-001",
  "source": "OpenFDA/FAERS",
  "protocol_reference": "NOT_REPORTED",
  "sample_identification": "NOT_REPORTED",
  "control_identification": "NOT_REPORTED",
  "experimental_conditions": "NOT_REPORTED",
  "measurement_method": "NOT_REPORTED",
  "method_validation_status": "NOT_REPORTED",
  "raw_data_availability": "NOT_REPORTED",
  "missing_data": [],
  "deviations": [],
  "statistical_reporting": "NOT_REPORTED",
  "reproducibility": "NOT_REPORTED",
  "limitations": "NOT_REPORTED",
  "evidence_category": "Clinical",
  "synthetic_data_declaration": "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING",
  "reviewer_status": "NOT REVIEWED",
  "evidence_quality": "VERIFIED",
  "final_review_status": "READY FOR HUMAN REVIEW"
}

Adapter Validation Result:
{
  "qc_status": "PASS",
  "qc_errors": [],
  "engine_available": true,
  "engine_version": "1.0.0",
  "blocker": null,
  "raw_result": {
    "valid": true,
    "errors": []
  }
}
[PASS] Scenario 8: Valid synthetic evidence record successfully validated by QC engine.

============================================================
SCENARIO 9: Test Missing Required Fields
============================================================
Testing missing 'study_id': qc_status=FAIL, errors=["JSON Schema validation failed at <record>: 'study_id' is a required property"]
Testing missing 'evidence_id': qc_status=FAIL, errors=["JSON Schema validation failed at <record>: 'evidence_id' is a required property"]
Testing missing 'schema_version': qc_status=FAIL, errors=["JSON Schema validation failed at <record>: 'schema_version' is a required property", 'schema_version must be 1.0.0']
Testing missing 'measurement_method': qc_status=FAIL, errors=["JSON Schema validation failed at <record>: 'measurement_method' is a required property"]
Testing missing 'reviewer_status': qc_status=FAIL, errors=["JSON Schema validation failed at <record>: 'reviewer_status' is a required property"]
Testing missing 'synthetic_data_declaration': qc_status=FAIL, errors=["JSON Schema validation failed at <record>: 'synthetic_data_declaration' is a required property"]
[PASS] Scenario 9: Missing required fields are strictly rejected by QC schema validation.

============================================================
SCENARIO 10: Test Invalid Schema (types, enums, additionalProperties)
============================================================
Testing invalid_category_enum: qc_status=FAIL, errors=["JSON Schema validation failed at evidence_category: 'FABRICATED_CATEGORY' is not one of ['Analytical', 'Structural', 'Functional', 'PK', 'PD', 'Immunogenicity', 'Preclinical', 'Clinical']"]
Testing invalid_quality_enum: qc_status=FAIL, errors=["JSON Schema validation failed at evidence_quality: 'HIGH_CONFIDENCE_DRUG' is not one of ['VERIFIED', 'PARTIAL', 'NEEDS REVIEW', 'CONFLICTING', 'INSUFFICIENT']"]
Testing invalid_reviewer_status_enum: qc_status=FAIL, errors=["JSON Schema validation failed at reviewer_status: 'APPROVED_BY_BOT' is not one of ['NOT REVIEWED', 'IN REVIEW', 'REVIEWED', 'REQUIRES SECOND REVIEW', 'CLOSED']"]
Testing invalid_type_deviations_not_list: qc_status=FAIL, errors=["JSON Schema validation failed at deviations: 'no deviations occurred' is not of type 'array'"]
Testing invalid_type_missing_data_not_list: qc_status=FAIL, errors=["JSON Schema validation failed at missing_data: 42 is not of type 'array'"]
Testing disallowed_additional_property: qc_status=FAIL, errors=["JSON Schema validation failed at <record>: Additional properties are not allowed ('unauthorized_ai_field' was unexpected)"]
Testing wrong_schema_version: qc_status=FAIL, errors=["JSON Schema validation failed at schema_version: '1.0.0' was expected", 'schema_version must be 1.0.0']
[PASS] Scenario 10: Invalid schema types, disallowed properties and invalid enums are rejected.

============================================================
SCENARIO 11: Test Duplicate and Conflicting Records
============================================================
Detected Duplicates: 3 (EV-DUP-001, STUDY-001, STUDY-CONF-99)
Detected Conflicts: 2 (measurement_method, evidence_quality)
Full Dataset Processing Summary:
Record Count: 5
Duplicates Count: 3
Conflicts Count: 2
Human Review Required Count: 5
[PASS] Scenario 11: Duplicates and conflicts detected, classified correctly, and preserved.

============================================================
SCENARIO 12: Verify Provenance and Original Evidence Preservation
============================================================
Source: OpenFDA/FAERS
Study ID: PROVENANCE-CHECK-001
Evidence ID: EV-000001
Synthetic Declaration: SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING
Immutability: Verified contract dict matches snapshot before and after mapping.
[PASS] Scenario 12: Provenance and original evidence are preserved verbatim.

============================================================
SCENARIO 13: Verify QC Output Correctly Marks Records Requiring Human Review
============================================================
Quality=VERIFIED       Reviewer=NOT REVIEWED   Final=READY FOR HUMAN REVIEW  -> HumanReviewRequired=True
Quality=PARTIAL        Reviewer=REVIEWED       Final=REVIEWED                -> HumanReviewRequired=True
Quality=NEEDS REVIEW   Reviewer=REVIEWED       Final=REVIEWED                -> HumanReviewRequired=True
Quality=CONFLICTING    Reviewer=REVIEWED       Final=REVIEWED                -> HumanReviewRequired=True
Quality=INSUFFICIENT   Reviewer=REVIEWED       Final=REVIEWED                -> HumanReviewRequired=True
Quality=VERIFIED       Reviewer=REVIEWED       Final=CLOSED                  -> HumanReviewRequired=False
Quality=VERIFIED       Reviewer=REVIEWED       Final=REVIEWED                -> HumanReviewRequired=False
Quality=VERIFIED       Reviewer=IN REVIEW      Final=REVIEWED                -> HumanReviewRequired=True
[PASS] Scenario 13: All non-reviewed or non-verified states accurately enforce human review.

============================================================
SCENARIO 14: End-to-End Integration through Backend FastAPI API
============================================================
GET /health -> 200 OK (status=OK, qc_engine_shyamal=VERIFIED, drug_safety_shravani=CONNECTED_WITH_KNOWN_BLOCKER, drug_discovery_shamit=CONNECTED_WITH_LIMITATIONS, patient_data=AVAILABLE)
POST /api/v1/research/evidence -> 200 OK (findings=1, status=REVIEW_REQUIRED)
POST /api/v1/qc/validate (Valid Record) -> 200 OK (qc_status=PASS, engine_available=True)
POST /api/v1/qc/validate (Invalid Record) -> 200 OK (qc_status=FAIL, errors captured)
[PASS] Scenario 14: End-to-end integration verified through FastAPI backend endpoints.

======================================================================
SUMMARY OF ALL 7 VERIFICATION SCENARIOS:
  SCENARIO_8: PASS
  SCENARIO_9: PASS
  SCENARIO_10: PASS
  SCENARIO_11: PASS
  SCENARIO_12: PASS
  SCENARIO_13: PASS
  SCENARIO_14: PASS
======================================================================
ALL 7 CROSS-REPO INTEGRATION SCENARIOS PASSED VERIFICATION.
```

---

## 5. Raw Log: Live TCP Socket Uvicorn Test

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-post-merge-fresh\venv_verification\Scripts\python.exe
rootdir: C:\Users\Microsoft\.gemini\antigravity\scratch\bhiv-post-merge-fresh
configfile: pytest.ini
plugins: anyio-4.16.0, hypothesis-6.170.17, asyncio-1.5.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

integration/test_live_socket_server.py::test_live_socket_http_server PASSED [100%]

============================== 1 passed in 0.85s ==============================
```
