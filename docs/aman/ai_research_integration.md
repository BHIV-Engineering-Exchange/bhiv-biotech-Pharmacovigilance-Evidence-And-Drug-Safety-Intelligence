# Aman Pal — AI Research Integration

## Existing components reused

- `openfda_connector.py`
- `normalize_evidence.py`
- `evidence_schema.py`
- `entity_resolution.py`

## Implemented workflow

The smallest real workflow is implemented in `research_integration.py`:

1. Accept a report containing `report_id` and `drug_name`.
2. Validate required fields.
3. Preserve the original report in `original_report`.
4. Normalize only the lookup input.
5. Retrieve OpenFDA/FAERS evidence.
6. Normalize and validate source records.
7. Preserve source ID, database, publisher, URL and retrieval time.
8. Mark findings as `SOURCE_DERIVED`; no model-generated summary is created.
9. Return uncertainty and missing-evidence details.
10. Return `human_review.required=true` and `status=PENDING`.

## Clinical boundaries

The workflow does not:

- diagnose a patient
- prescribe or recommend treatment
- infer causality
- establish clinical validity
- generate patient-specific conclusions

FAERS records are spontaneous reports and require independent review.

## Live verification

An actual `ibuprofen` lookup returned `REVIEW_REQUIRED`, one `IBUPROFEN` FAERS record, a source record ID and retrieval URL. The finding was explicitly marked as source-derived.

## Blockers

- No PharmGKB/ClinPGx or other pharmacogenomic source connector was found.
- No PubMed or general medical-evidence connector was found.
- No approved human-review workflow or researcher routing service was found.
- No ML model or inference capability was found.
