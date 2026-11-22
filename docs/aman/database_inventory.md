# Aman Pal — Database and Storage Inventory

## Storage type

- Primary persistent implementation: JSON file storage
- Default file: `evidence_output.json`
- Implemented by: `evidence_store.py`

## Data model

Evidence records use `EvidenceRecord` / `evidence_schema.py` fields:

- evidence identifier
- drug name and identifier
- adverse event
- association type
- source, source record identifier and URL
- evidence type and event date
- retrieval timestamp
- provenance
- raw-record reference
- entity-resolution status and canonical entity
- data origin

## Validation

`validate_evidence()` checks required fields, types, provenance, entity-resolution status, association type and data origin.

## Migration and runtime status

- No SQL/NoSQL database connection found
- No migration framework or migration files found
- JSON storage availability: implementation verified by temporary-path tests
- No live external database service was available or configured
