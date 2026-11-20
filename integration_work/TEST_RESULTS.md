# Drug Safety Evidence Integration — Test Results

Date: 20 November 2026

## Integration Tests
Command:
python -m pytest integration_work/test_drug_safety_integration.py -v

Result:
10 passed, 0 failed

## Full Receiver Regression Suite
Command:
python -m pytest -v

Result:
57 passed, 0 failed

## Integration Test Coverage
1. Actual producer input record count
2. Producer schema preservation
3. Invalid JSON wrapper rejection
4. Missing records array rejection
5. Incorrect record count rejection
6. Exact duplicate detection
7. Same source identifier with different content
8. Unrelated record handling
9. Producer-reported conflict preservation
10. Human-review lifecycle validation

## Regression Coverage
- End-to-end pipeline
- Entity resolution
- Error handling
- Evidence schema validation
- Evidence storage
- Monitoring
- Normalization
- Source retrieval
- Provenance preservation
- Duplicate handling

## Result
All 57 tests passed.

No existing receiver regression test failed.

## Important Integration Boundary
These results demonstrate local staging and test execution.
They do not establish production ingestion, canonical schema approval,
clinical causality, clinical safety, or regulatory approval.
