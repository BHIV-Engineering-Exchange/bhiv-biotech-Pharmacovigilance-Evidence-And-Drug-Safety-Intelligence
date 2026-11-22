# Aman Pal — API and Dependency Map

## OpenFDA API

| Field | Value |
|---|---|
| Service | OpenFDA drug adverse-event endpoint |
| Endpoint | `GET https://api.fda.gov/drug/event.json` |
| Input | Query `search=patient.drug.medicinalproduct:"<drug>"`, integer `limit`, timeout 30 seconds |
| Output | JSON object containing `results`; connector returns normalized status/result fields |
| Authentication | None configured |
| Dependencies | `requests>=2.31.0` |
| Runtime availability | Verified live; an `ibuprofen` request returned one record |
| Integration status | Live source retrieval verified |

## Research workflow interface

`run_research_workflow(report, limit=5, retriever=search_drug)`

Required report fields:

- `report_id`: non-empty string
- `drug_name`: non-empty string

Output:

- `status`: `REVIEW_REQUIRED`, `NO_EVIDENCE`, `INVALID_INPUT`, or `SOURCE_UNAVAILABLE`
- `original_report`: original value preserved
- `normalized_input`: validated report fields and normalized drug query
- `findings`: normalized evidence plus source metadata
- `uncertainty`: evidence limitations and missing evidence
- `human_review`: pending review route

No HTTP service endpoint is implemented. The workflow is an importable Python interface.

## Dependencies

- Python >=3.10
- Runtime: `requests>=2.31.0`
- Test: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `hypothesis>=6.100.0`

## Environment variables

- None required or identified for the OpenFDA integration
- No secrets were found in project configuration
