# Drug Safety Evidence Integration — Technical Handover

Date: 22 November 2026  
Project: BHIV Biotech — Drug Safety Evidence Integration  
Status: Local staging integration prototype; production integration pending.

---

## 1. Objective

Prepare an integration boundary between the existing Drug Safety QC Evidence
producer and the Biomedical Evidence Engine receiver.

The implementation focuses on:
- Preserving original producer evidence.
- Mapping producer records into a receiver-compatible structure.
- Validating records against the receiver schema.
- Reporting missing fields and validation errors.
- Identifying duplicate and potentially conflicting evidence.
- Preserving producer-reported conflicts.
- Creating human-review workflow records.
- Avoiding automatic clinical or regulatory conclusions.

## 2. Project Locations

Producer project:  
Drug_Safety_QC_Evidence_Map

Receiver project:  
bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence

Integration workspace:  
integration_work/

## 3. Files Created

- drug_safety_input.json  
  Staged copy of the producer's normalized evidence input.

- drug_safety_import_adapter.py  
  Reads the producer wrapper, extracts records, maps fields, validates
  candidate receiver records, and generates staging/QC outputs.

- staged_receiver_records.json  
  Contains mapped records and preserved original producer records.

- drug_safety_qc_report.json  
  Contains receiver validation results, processing status,
  duplicate/conflict findings, and human-review information.

- duplicate_conflict_checks.py  
  Identifies exact duplicates, potential duplicates, and same-source-ID
  records with different content. Does not delete or merge evidence.

- review_lifecycle.py  
  Implements controlled review states and reviewer identity requirements.

- test_drug_safety_integration.py  
  Contains 14 automated integration tests.

- TEST_RESULTS.md  
  Records integration and full regression test results.

## 4. Input and Provenance

Producer input format:

{
  "schema_name": "BHIV_Drug_Safety_Evidence",
  "schema_version": "1.0.0",
  "record_count": 10,
  "records": []
}

The staged input contains 10 records, EV001 through EV010.

The source file was copied without changing its contents.
The source and staged input SHA256 hashes matched:

1061230F77A5E5395FFC1673083EB0EDB2C7965CAD6D9034D58DC7DD1D09E725

Original evidence IDs, producer fields, and provenance information
are preserved in the staging output.

## 5. Proposed Field Mapping

| Producer field | Proposed receiver mapping |
|---|---|
| drug_product_identifier | drug_name |
| original_evidence_id | source_record_id |
| ingestion_timestamp | retrieved_at |
| original_source | provenance.source_system |
| transformation_path | Preserved separately |
| source_version | Preserved separately |
| observation | Preserved as original observation |
| drug identifier | Unresolved; not invented |
| source URL | Missing; not invented |

Important:  
These are prototype mappings, not an approved canonical contract.
The proposed retrieved_at and provenance mappings require confirmation.
The receiver's transformation structure also requires agreement.

## 6. Receiver Validation Results

Total records staged: 10  
Receiver-valid records: 0  
Receiver-invalid records: 10

The receiver validation identifies these missing fields:

- source_url: missing in 10 records
- provenance.underlying_dataset: missing in 10 records
- provenance.retrieval_method: missing in 10 records
- provenance.transformation: missing in 10 records

Invalid records are retained in staging.  
They are not silently discarded or written into the permanent receiver store.

## 7. Duplicate and Conflict Results

Records examined: 10  
Duplicate relationships detected: 0  
Source-reported conflicts preserved: 1

EV009 retains its producer-reported Conflicting status.

No automatic conflict was inferred between EV003 and EV009.

The duplicate/conflict checker:
- Identifies exact duplicate relationships.
- Flags same source identifiers with different content.
- Identifies potential duplicates for review.
- Preserves source-reported conflict status.
- Does not delete or merge evidence.

## 8. Human Review

All 10 staged records currently require human review.

Initial review status: PENDING

The workflow supports:
- PENDING
- IN_REVIEW
- COMPLETED
- ESCALATED

A reviewer ID is required for transitions.  
Direct completion from PENDING is rejected.  
Completed reviews cannot be reopened through the implemented transitions.

Safety confirmation and causality confirmation remain false by default.

These are workflow controls, not evidence that a human reviewer has
actually completed or approved any record.

## 9. Test Results

Integration tests:  
14 passed, 0 failed.

Full receiver regression suite:  
61 passed, 0 failed.

Coverage includes:
- Producer input and schema checks.
- Invalid wrapper handling.
- Missing records array.
- Record count mismatch.
- Duplicate detection.
- Same source ID with different content.
- Unrelated records.
- Producer conflict preservation.
- Human-review lifecycle.
- Receiver end-to-end pipeline.
- Entity resolution.
- Schema and provenance validation.
- Evidence storage and duplicate handling.
- Source retrieval and monitoring.

See TEST_RESULTS.md for recorded results.

## 10. Execution Instructions

Run the staging adapter from the receiver project root:

& ".\.venv\Scripts\python.exe" -c "import runpy; runpy.run_path('integration_work/drug_safety_import_adapter.py', run_name='__main__')"

Run integration tests:

& ".\.venv\Scripts\python.exe" -m pytest integration_work\test_drug_safety_integration.py -v

Run the full receiver regression suite:

& ".\.venv\Scripts\python.exe" -m pytest -v

## 11. Data Governance and Safety Boundaries

The implementation does not:
- Establish clinical causality.
- Confirm clinical safety or efficacy.
- Make treatment decisions.
- Make regulatory approval decisions.
- Automatically resolve uncertain evidence.
- Replace professional review.
- Treat producer validation as proof of scientific truth.

Original evidence and uncertainty must remain traceable.

The producer's validation status and the receiver's structural validation
are separate assessments and must not be conflated.

Synthetic-data status is not fully declared in the producer schema.
EV005 is explicitly fictional. Other records with demonstration-like
content must not be presented as verified source data without confirmation.

## 12. Pending Decisions and Dependencies

The following remain open before production integration:

1. Approval of the shared canonical evidence schema.
2. Confirmation of the producer-to-receiver field mapping.
3. Approval of provenance transformation structure.
4. Provision or confirmation of source URLs and retrieval methods.
5. Explicit real/synthetic/unknown data classification.
6. Confirmation of drug identity and identifier mapping.
7. Agreement on invalid-record retention and receiver ingestion behavior.
8. Agreement on duplicate and conflict handling.
9. Confirmation of the human-review handoff and ownership.
10. Integration boundary approval by the responsible teams.

Coordination required with:
- Backend team: receiver import and storage contract.
- QC team: validation and quality-report contract.
- UI team: reviewer workflow and review visibility.
- Schema/provenance governance owners: canonical schema and lineage approval.

## 13. Current Delivery Status

Completed:
- Producer input copied and integrity checked.
- Local staging adapter created.
- Candidate receiver mapping implemented.
- Receiver validation executed.
- Missing provenance fields reported.
- Duplicate/conflict checks implemented.
- Human-review lifecycle implemented.
- Integration tests: 14/14 passed.
- Full receiver regression: 61/61 passed.
- Permanent receiver store protected during staging tests.
- Test results and handover documentation prepared.

Not yet completed:
- Approved shared schema.
- Approved provenance mapping.
- Production receiver ingestion.
- Live cross-team integration.
- Actual human review completion.
- Final upstream repository submission/merge.

## 14. Final Status Statement

This delivery demonstrates a locally tested, isolated drug-safety evidence
staging and integration prototype with provenance preservation, receiver
validation, duplicate/conflict reporting, and human-review workflow controls.

It is not a completed production integration. Production readiness depends
on the pending schema, provenance, data-classification, and receiver
contract approvals listed above.
## 15. Additional Verification — 22 November 2026

### 15.1 Native Biomedical Evidence Engine Validation

A separate read-only verification was performed using the existing
OpenFDA connector and native receiver normalization pipeline.

Test source: OpenFDA / FAERS  
Requested drug: ibuprofen  
Retrieved source record ID: 10003301  
Receiver schema version: 1.1

Receiver provenance:
- source_system: OpenFDA
- underlying_dataset: FAERS
- retrieval_method: REST API
- transformation: raw JSON -> normalized evidence

Result:
- Retrieval: SUCCESS
- Normalization: SUCCESS
- Receiver validation: VALID
- Validation errors: None
- Permanent storage modified: No

This confirms that the native receiver can successfully normalize and
validate a genuine OpenFDA record.

It does NOT demonstrate successful import of a Drug Safety producer
record. The OpenFDA record is a separate source record and has not
been substituted for the Drug Safety fixture.

### 15.2 Drug Safety Source Artifact Verification

The Drug Safety producer fixture contains 10 records, EV001 through EV010.

A matching CSV artifact was located in the Drug Safety producer project:

`evidence_packet/code_packet/source_artifacts/evidence_records.csv`

GitHub repository:
https://github.com/BHIV-Engineering-Exchange/bhiv-biotech-Drug_Safety_QC_Evidence_Map

The uploaded CSV was downloaded from GitHub and its SHA256 checksum was verified against the local source copy.

SHA256:

`9D3251B4A0AC9001E8E9C6D80F932013C687B5B42755035CA2648DF067FA02C9`

CSV-to-JSON comparison:
- CSV records: 10
- JSON records: 10
- Evidence IDs matched: 10/10
- Source fields matched: 10/10
- Drug product fields matched: 10/10
- Observation fields matched: 10/10
- Date fields matched: 10/10

This establishes that the CSV is a matching source artifact for the staged producer records.

Limitation: Its identity as the original file referenced by `existing_test1_csv` has not yet been independently confirmed. The CSV comparison does not establish external source URLs, underlying datasets, retrieval methods, or record-level transformation provenance.

Current result:
- Matching CSV artifact located and preserved in the producer repository.
- GitHub and local CSV SHA256: MATCH.
- CSV-to-JSON record comparison: 10/10 MATCH.
- Native receiver valid-record test: PASSED separately.
- Drug Safety producer-to-receiver valid-record test: BLOCKED.
- Receiver validation of the 10 staged producer records: 0 valid, 10 invalid.
- Permanent receiver storage: NOT MODIFIED.

### 15.3 Required Next Action

The Drug Safety producer owner or responsible source-data owner must
provide the original source artifact or independently verifiable
record-level provenance.

The responsible schema/provenance owners must confirm the approved
field mapping and transformation representation.

After these dependencies are resolved, rerun the producer-to-receiver
valid-record test and record its raw output.

Until then, retain the valid-record integration case as BLOCKED,
not PASSED.

### Mapping Approval Authority Clarification

It has been clarified that temporary repository maintenance responsibility does not authorize Shravani Jambhulkar to formally approve the Drug Safety producer-to-receiver mapping.

MDU retains ownership of schemas, provenance and lineage.

The proposed mapping will remain:

`PROPOSED_MAPPING_PENDING_APPROVAL`

Shravani may continue technical review, compatibility assessment, testing and documentation of recommended corrections.

Formal approval must be obtained from Surendra or the officially designated MDU/schema authority.

If Surendra remains unavailable, the approval request must be escalated to the designated schema/provenance authority.

Following approval, the integration documentation must record:

- Approver's name and authority.
- Approval date.
- Approved schema version.
- Approved mapping version.

**Current decision: Technical review permitted; formal mapping approval pending.**

