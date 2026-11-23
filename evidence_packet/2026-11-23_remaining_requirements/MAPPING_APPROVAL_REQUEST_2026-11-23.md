# Drug Safety Producer-to-Receiver Mapping Approval Request

Date: 2026-11-23

## 1. Purpose

Request formal review and approval of the proposed integration mapping between:

Producer:
BHIV Drug Safety Evidence
Schema: BHIV_Drug_Safety_Evidence v1.0.0

Receiver:
Biomedical Evidence Engine
Schema: EvidenceRecord v1.1

## 2. Current approval status

PROPOSED_MAPPING_PENDING_APPROVAL

This mapping has undergone technical implementation and compatibility testing.
Technical testing does not constitute schema or governance approval.

## 3. Approval authority requested

Required reviewer:
Surendra or officially designated MDU/schema/provenance authority.

The temporary repository maintainer is not claiming authority to approve shared schemas, provenance definitions, lineage or producer-to-receiver mapping.

## 4. Items requiring confirmation

1. Acceptance of the producer-to-receiver field mapping.
2. Confirmation of required receiver provenance fields.
3. Confirmation of source_url and underlying_dataset requirements.
4. Confirmation of retrieval_method and transformation requirements.
5. Confirmation that producer source_version and schema_version remain distinct.
6. Confirmation that producer transformation_path is preserved.
7. Confirmation of synthetic_data_status handling.
8. Confirmation of invalid-record preservation and human-review handling.
9. Confirmation of duplicate and conflict handling.
10. Confirmation of the receiver QC output and error-report contract.

## 5. Technical evidence available

- Producer canonical schema and normalized JSON.
- Receiver integration adapter.
- Producer-to-receiver mapping documentation.
- 14 integration tests passed.
- 61 receiver regression tests passed.
- All 10 staged Drug Safety records currently fail receiver validation because required source URL and receiver provenance fields are missing.
- Invalid records and unresolved review items are preserved.
- Permanent receiver storage remains unchanged.

## 6. Required approval record

The approving authority must provide:

- Approver name and role.
- Approval date.
- Approved producer schema version.
- Approved receiver schema version.
- Approved mapping version.
- Explicit approval or requested corrections.

## 7. Current decision

No formal mapping approval is claimed.

The mapping remains:
PROPOSED_MAPPING_PENDING_APPROVAL

No production integration or PR merge is authorized by this request.

## 8. Requested response

Please review the proposed mapping and either:

A. Explicitly approve it with the approval details above; or

B. Provide corrections and required changes before approval.
