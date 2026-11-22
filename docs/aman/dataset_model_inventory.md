# Aman Pal — Dataset and Model Inventory

## Datasets

### Live evidence source

- Source: OpenFDA
- Dataset: FAERS adverse-event reports
- Format: REST JSON
- Provenance: source record ID, source URL and retrieval timestamp are preserved
- Validation: normalization plus evidence-schema validation
- Data origin: `REAL_WORLD`

### Stored evidence

- File: `evidence_output.json`
- Format: JSON array
- Validation/status: existing data should be treated according to existing pipeline schema
- No separate dataset provenance manifest was found

### Synthetic fixtures

- Synthetic test reports are embedded in `test_research_integration.py`
- OpenFDA-style records are embedded in test modules
- Synthetic/report fixtures are identified with `SYN-` and test record IDs

## Pretrained/custom ML models

- No pretrained model or custom model file was found
- No model inference interface was found
- Entity resolution is deterministic string matching, not machine learning
- The research workflow uses source-derived evidence and performs no model-generated clinical summary

## Research retrieval

- Verified capability: live OpenFDA retrieval
- No PubMed, ClinPGx, PharmGKB or separate pharmacogenomic connector was found or verified
