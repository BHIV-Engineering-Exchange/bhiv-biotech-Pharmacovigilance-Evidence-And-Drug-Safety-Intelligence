# Drug Safety Evidence Integration — Consolidated Handover

**Date:** 23 November 2026  
**Workstream:** BHIV Drug Safety Evidence Integration  
**Technical maintainer:** Shravani Jambhulkar  
**Receiver repository:** Biomedical Evidence Engine  
**Related PR:** https://github.com/BHIV-Engineering-Exchange/bhiv-biotech-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence/pull/1

## 1. Executive Summary

Technical inspection, staging, testing and evidence collection have been performed for the Drug Safety producer-to-receiver integration.

The original 10 producer records remain preserved. Receiver validation identified missing source URL and required receiver provenance fields. These records were not artificially modified to pass validation.

A separate genuine OpenFDA/FAERS record was retrieved, normalized through the receiver's native normalizer and successfully validated against receiver schema version 1.1.

The producer-to-receiver mapping remains proposed and pending approval by the authorized schema/provenance owner.

## 2. Status of the Four Remaining Requirements

### Requirement 1 — Original source artifact integrity

**Status: TECHNICAL INTEGRITY VERIFIED; ORIGINAL SOURCE IDENTITY NOT ESTABLISHED**

The local evidence_records.csv file was compared with the file retrieved from the original GitHub commit.

- Original GitHub commit: 6a4cdfe59b0eaf2b809657997a299eb81c682fba
- GitHub blob SHA: f419e9cbabf69db0c174501542ffef311c78ae2e
- File size: 2,942 bytes
- SHA-256: 9D3251B4A0AC9001E8E9C6D80F932013C687B5B42755035CA2648DF067FA02C9
- Local and downloaded GitHub copies had matching SHA-256 hashes.

This establishes byte-level integrity against the committed GitHub artifact. It does not independently establish that the original file was externally sourced under the name existing_test1_csv.

Supporting report:
CSV_ARTIFACT_INTEGRITY_VERIFICATION_2026-11-23.md

### Requirement 2 — Record-level source provenance

**Status: AUDIT COMPLETED; SOURCE-LEVEL GAPS REMAIN**

The 10 producer records were reviewed for source URL, original source record identifier, underlying dataset, retrieval method and transformation details.

The producer CSV does not contain the source-level metadata required to independently retrieve and verify each original record.

The producer normalizer declares source_version as existing_test1_csv and records a local transformation path. These values do not establish original source retrieval details.

Missing or incomplete source identifiers and URLs were documented. No source URLs, dataset identifiers or retrieval methods were invented.

Supporting report:
DRUG_SAFETY_RECORD_LEVEL_PROVENANCE_AUDIT_2026-11-23.md

### Requirement 3 — Shared schema and field mapping approval

**Status: APPROVAL REQUEST PREPARED; FORMAL APPROVAL PENDING**

The proposed mapping between:

- Producer: BHIV_Drug_Safety_Evidence v1.0.0
- Receiver: EvidenceRecord v1.1

has been documented for review.

The request covers provenance requirements, source_version versus schema_version, transformation_path preservation, synthetic-data status, invalid-record handling, duplicate/conflict handling and receiver QC.

The mapping status remains:

PROPOSED_MAPPING_PENDING_APPROVAL

No formal schema or mapping approval is claimed. Approval must come from Surendra or the officially designated MDU/schema/provenance authority.

Supporting report:
MAPPING_APPROVAL_REQUEST_2026-11-23.md

### Requirement 4 — Receiver-valid genuine Drug Safety evidence and QC

**Status: NATIVE RECEIVER VALIDATION DEMONSTRATED**

A fresh OpenFDA/FAERS retrieval was performed for ibuprofen.

Selected source record:

- FAERS report ID: 10003301
- Drug: IBUPROFEN
- Reported adverse event: Dyspepsia
- Source: OpenFDA/FAERS
- Underlying dataset: FAERS
- Retrieval method: REST API
- Receiver schema version: 1.1
- Entity resolution: MATCHED
- Association type: REPORTED_ASSOCIATION
- Receiver validation: VALID
- Validation errors: 0

The original raw record was normalized using the receiver's native normalizer and validated using the receiver's validate_evidence function.

The evidence package contains:

1. 01_raw_faers_source_record.json
2. 02_normalized_receiver_record.json
3. 03_receiver_qc_report.json
4. 04_execution_summary.json

Permanent evidence storage was not modified.

This demonstrates successful native receiver validation of one genuine OpenFDA/FAERS record. It does not establish that the 10 producer records passed receiver validation or that the proposed producer-to-receiver mapping has been approved.

## 3. Integration Test Results

Previously recorded integration and receiver regression results:

- Integration tests: 14 passed.
- Full receiver regression tests: 61 passed.

The 10 staged producer records remain receiver-invalid because required source URL and receiver provenance fields are missing.

The staged records and human-review requirements remain preserved. The EV009 conflict remains available for review.

No permanent evidence-store write was performed by the staging adapter.

## 4. Governance and Safety Boundaries

- No automatic causality determination is claimed.
- Reported association is not proof of causation.
- Invalid producer records are not represented as receiver-valid.
- Missing source provenance has not been fabricated.
- Duplicate and conflict findings remain distinct.
- Unresolved evidence remains subject to human review.
- The producer-to-receiver mapping remains pending authorized approval.
- No production integration or PR merge is claimed.

## 5. Outstanding Actions

| Responsible owner | Required action |
|---|---|
| Drug Safety source owner | Supply original source artifacts or verifiable source-level provenance for the 10 producer records. |
| Surendra or designated MDU/schema authority | Review and formally approve or reject the proposed shared schema mapping. |
| Receiver/backend owner | Confirm the receiver import and provenance contract. |
| QC owner | Confirm the accepted QC and error-report contract. |
| Integration owner | Confirm the approved execution and handoff process. |

After approval, record the approver's name and role, approval date, schema version and mapping version.

## 6. Evidence Folder

This handover folder contains the three supporting audit documents.

The native OpenFDA receiver validation evidence is stored separately in:

evidence_packet/point4_openfda_receiver_validation_2026-11-23/

## 7. Final Handover Statement

The technical review and evidence collection have produced a reproducible native receiver validation demonstration and documented the outstanding producer provenance and governance dependencies.

The current result is a technically tested, staged integration with one successful native OpenFDA receiver-validation demonstration.

The complete 10-record Drug Safety producer exchange is not yet receiver-valid. Formal mapping approval and source-level provenance remediation remain outstanding.

**Final mapping status: PROPOSED_MAPPING_PENDING_APPROVAL**
