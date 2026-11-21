Biomedical Evidence Engine
EOD Audit and Inherited-Work Handover Report
Organization: BHIV Biotech  
Audit owner: Drug Safety Intelligence Lead  
Inherited workstream: Surendra's Biomedical Evidence Engine  
Audit date: 17 November 2026  
Repository: bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence
1. Executive Summary
A fresh local inspection and verification of the inherited Biomedical Evidence Engine was completed.
The repository successfully passed all 47 automated tests. The OpenFDA connector also successfully retrieved five records from the live OpenFDA/FAERS endpoint.
However, the audit identified important data-quality and traceability limitations involving evidence ID generation, multi-drug report normalization, event-date extraction, schema validation, and persistence behavior.
The inherited project has a runnable and test-passing local baseline, but further remediation and integration validation are required before it can be considered production-ready.
2. Verification Results
Automated testing
Tests collected: 47
Tests passed: 47
Tests failed: 0
Pytest exit code: 0
Python version: 3.14.7
Pytest version: 9.2.0
Live source retrieval
Source: OpenFDA/FAERS
Requested medicine: Ibuprofen
Records retrieved: 5
API result: Success
Retrieval timestamp: 2026-11-17T09:11:28.405557+00:00
Normalization and validation
Records processed: 5
Records passing current schema validation: 5
Entity resolution: 1 MATCHED and 4 UNRESOLVED
Passing the existing validator does not establish clinical correctness or completeness.
3. Historical Evidence Dataset Audit
The existing evidence_output.json file was inspected.
Total stored records: 15
Unique evidence IDs: 5
Unique source record IDs: 15
Missing event dates: 15
Missing drug names: 0
Missing adverse-event descriptions: 0
Missing source URLs: 0
Missing provenance: 0
Association semantics: REPORTED_ASSOCIATION for all 15 records
Entity resolution: 14 UNRESOLVED and 1 MATCHED
The historical records have consistent structural fields, but their original source authenticity was not independently established during this audit.
4. Confirmed Critical Finding: Duplicate Evidence IDs
The evidence ID generator supports source-record-based identifiers, but normalize_evidence.py calls:
generate_evidence_id(index)
It does not pass the extracted source_record_id.
Consequently, the index-based identifier restarts when a new batch is normalized.
Observed result:
15 records
Only 5 unique evidence IDs
Multiple different source records share the same evidence ID.
Recommended correction:
generate_evidence_id(index, source_record_id)
This correction is proposed and has not been applied to the inherited repository.
Risk: Duplicate evidence IDs can impair traceability, record referencing, and downstream integration.
5. Confirmed Ingestion Discrepancy
The live OpenFDA response was inspected for all five reports.
All five reports contained ibuprofen in their reported drug lists. However, the normalization function extracts only the first listed drug.
As a result, four normalized records represented other medicines rather than the requested medicine.
The likely cause is the following implementation behavior:
Read the drug list.
Select only the first drug.
Use that drug for normalization and entity resolution.
Recommended correction:
Preserve all reported medicines.
Identify the requested medicine wherever it appears in the report.
Maintain the distinction between reported medicines and suspected medicines.
Avoid interpreting a reported association as proof of causality.
6. Additional Technical Limitations
Normalization
Only the first drug and first reaction are extracted.
Event date is currently assigned None.
The normalized evidence record does not preserve the complete raw report.
Evidence IDs are index-based in the current normalization call.
Schema validation
Required-field checks exist.
Provenance and association semantics are checked.
Strict data-type validation is limited.
Event-date completeness and source-ID uniqueness are not enforced.
Several field-value constraints need stronger validation.
Evidence storage
Corrupted JSON may silently be interpreted as an empty dataset.
Direct file writes are used rather than an atomic replacement process.
A subsequent write after a corrupted-file fallback could risk overwriting existing data.
Error handling and monitoring
Errors are wrapped in structured results.
Raw exception messages may expose technical details.
Monitoring currently uses console logging.
Persistent log-file storage or centralized monitoring was not demonstrated.
Reproducibility
Automated tests passed.
Deterministic entity matching and fingerprinting are present.
Exact reproducibility of changing live API responses has not been established.
7. Preserved Audit Evidence
Separate audit directory:
Biomedical_Evidence_Engine_Inspection/fresh_verification_2026-11-17/
Files preserved:
pytest_fresh_2026-11-17.txt
live_openfda_verification.json
The test log records all 47 passing tests.
The OpenFDA verification JSON records the live retrieval result, timestamp, source URL, and report identifiers.
The JSON file was successfully validated.
8. Recommended Remediation Priorities
Priority 1 — Evidence identity
Generate evidence IDs using stable source record identifiers.
Add tests for duplicate IDs across separate ingestion batches.
Validate uniqueness before persistence.
Priority 2 — Multi-drug normalization
Preserve all medicines reported in each source record.
Match the requested medicine across the full drug list.
Preserve the original report relationship and association semantics.
Priority 3 — Provenance and completeness
Extract event dates where available.
Preserve traceable references to raw source records.
Explicitly distinguish real-source and synthetic/test records.
Priority 4 — Data integrity
Fail safely when stored JSON is corrupted.
Introduce atomic file writes and backup protection.
Add tests for conflicting source IDs and malformed persisted data.
Priority 5 — Validation and monitoring
Strengthen schema type and value validation.
Add persistent audit logging.
Review exception-message exposure.
Priority 6 — Cross-workstream integration
Implement the agreed JSON exchange contract.
Validate schema compatibility between the Drug Safety Evidence Integration workstream and Biomedical Evidence Engine.
Preserve human-review requirements for uncertain records.
9. Integration and Safety Boundaries
The intended integration should preserve the following responsibilities:
The producing Drug Safety workstream is responsible for its normalization, standardization, matching, provenance, and JSON export.
The receiving Biomedical Evidence Engine is responsible for import compatibility, ingestion validation, QC reporting, error handling, and downstream review routing.
Invalid or uncertain evidence must remain identifiable and traceable.
Conflicts and duplicates should be reported rather than silently discarded.
The system must not automatically make clinical causality assessments, clinical decisions, regulatory approval decisions, or treatment recommendations.
Human review remains necessary where evidence is uncertain.
The integration contract has been discussed and agreed in principle, but a complete cross-repository integration has not yet been verified.
10. Handover Status
Current status: RUNNABLE BASELINE — REMEDIATION REQUIRED
Completed:
Fresh local repository inspection.
Environment setup.
Automated test execution.
Live OpenFDA retrieval verification.
Normalization and validation inspection.
Historical dataset audit.
Evidence ID duplication investigation.
Ingestion discrepancy investigation.
Separate audit evidence preservation.
Not completed:
Source-code remediation.
Re-running tests after remediation.
Cross-repository integration execution.
Deployment or production verification.
Verification of the original Git commit history from the downloaded ZIP.
No intentional changes were made to the inherited source code or historical evidence dataset during this audit.
Final assessment: The inherited Biomedical Evidence Engine has a functioning, test-passing baseline and demonstrated live-source connectivity. Nevertheless, evidence identity and normalization limitations require correction before reliable downstream evidence integration.
