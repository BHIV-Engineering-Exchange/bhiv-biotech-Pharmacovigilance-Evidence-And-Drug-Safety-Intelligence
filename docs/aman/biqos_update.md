# Aman Pal — BIQOS Update Preparation

## Capability

- Capability name: Source-linked pharmacogenomic and medical research integration for the pharmacovigilance evidence pipeline
- Accountable owner: Aman Pal
- Canonical repository: `BHIV-Engineering-Exchange/bhiv-Live-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence-Pipeline-v1-AI-Biotech-Core-Task-1`
- Branch: `main`
- Commit: `ed7e12846b1e8fbf5afd01fd7106eff6be378a99`
- Runtime/deployment location: local Python importable workflow; not deployed
- Implementation status: Implemented
- Test status: Tested

## Implementation evidence

- Code: `research_integration.py`
- Tests: `test_research_integration.py`
- Documentation: `docs/aman/ai_research_integration.md`
- Test evidence: 59 tests passed
- Live evidence: OpenFDA returned one `ibuprofen` FAERS record

## Endpoint/contracts

The capability currently exposes only a Python function contract:

```text
run_research_workflow(report, limit=5, retriever=search_drug)
```

It does not expose an HTTP endpoint.

## Dependencies

- Python >=3.10
- `requests`
- Existing normalization, schema and entity-resolution modules
- Live OpenFDA/FAERS API

## Actual runtime state

- Reported: yes
- Implemented: yes
- Tested: yes
- Deployed: no
- Integrated: only source retrieval is integrated; no approved broader system integration is claimed
- Independently verified: live source retrieval and test suite verified

## Blockers and risks

- No additional authoritative pharmacogenomic/medical evidence connectors found
- No HTTP API or approved workflow executor contract found
- No approved human-review routing implementation found
- Live evidence is not evidence of clinical validity or causality

## BIQOS mechanism

No authorized BIQOS update mechanism or maintainer interface was found in this repository. This file is the exact prepared update for the BIQOS maintainer.
