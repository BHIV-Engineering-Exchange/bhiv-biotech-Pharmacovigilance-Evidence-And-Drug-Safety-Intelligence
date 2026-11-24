# Drug Safety Evidence Integration — Test Results

Date: 22 November 2026

## Integration Tests

Command:
```powershell
python -m pytest integration_work/test_drug_safety_integration.py -v
```

Result:
**14 passed, 0 failed**

## Full Receiver Regression Suite

Command:
```powershell
python -m pytest -v
```

Result:
**61 passed, 0 failed**

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
11. Missing required provenance rejection
12. Unknown drug match remains unresolved
13. Unknown synthetic-data status is preserved
14. Deterministic adapter output verification

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
- Drug Safety integration adapter

## Result

All 61 tests passed.

All 14 integration tests passed.
No existing receiver regression test failed.

## Important Integration Boundary

These results demonstrate local staging and test execution.

They do not establish production ingestion, canonical schema approval, clinical causality, clinical safety, or regulatory approval.

The current adapter output contains 10 staged records requiring human review. Receiver validation currently marks all 10 records invalid because required source and provenance information is missing.

The synthetic-data status remains unknown. No missing source or provenance information has been fabricated.
