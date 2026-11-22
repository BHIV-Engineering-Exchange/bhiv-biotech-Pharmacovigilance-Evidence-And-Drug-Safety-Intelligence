# Aman Pal — Test Baseline and Current Results

## Commands

Baseline before implementation:

```powershell
python --version
python -m pytest -q
```

Baseline result:

```text
Python 3.13.5
53 passed in 0.74s
```

After implementation:

```powershell
python -m pytest -q
```

Current result:

```text
59 passed in 0.55s
```

## Added coverage

The added `test_research_integration.py` covers:

- valid report and source-linked provenance
- invalid/incomplete report
- no matching evidence
- external source failure
- unexpected retriever response
- report validation contract

Existing tests continue to cover normalization, schema validation, storage, duplicate/conflict behavior, entity resolution, monitoring and error handling.

## Mock/live distinction

- Unit tests use mocked HTTP responses or injected retrievers where isolated behavior is being tested; this is explicitly identified in test code.
- Live OpenFDA connectivity was separately verified with a real API request.
- The live API result is not evidence of clinical validity or causality.
