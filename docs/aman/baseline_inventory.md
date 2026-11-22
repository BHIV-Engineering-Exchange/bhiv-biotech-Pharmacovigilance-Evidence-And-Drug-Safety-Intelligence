# Aman Pal — Independent Baseline Inventory

## Repository

- Canonical repository: `BHIV-Engineering-Exchange/bhiv-Live-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence-Pipeline-v1-AI-Biotech-Core-Task-1`
- Remote: `https://github.com/BHIV-Engineering-Exchange/bhiv-Live-Pharmacovigilance-Evidence-And-Drug-Safety-Intelligence-Pipeline-v1-AI-Biotech-Core-Task-1.git`
- Branch: `main`
- HEAD: `ed7e12846b1e8fbf5afd01fd7106eff6be378a99`
- Latest commit: `ed7e128 Add fresh test and OpenFDA verification evidence`
- Working tree: tracked files unchanged; existing untracked `.vscode/`

## Application

- Entry point: `app.py`
- Language/runtime: Python 3.13.5, project requires Python >=3.10
- Framework: command-line application using `requests`
- Package layout: compatibility package `src/` exposes repository-root modules through `src/__path__`

## Reusable modules

- `openfda_connector.py`: OpenFDA/FAERS retrieval and request error handling
- `entity_resolution.py`: conservative exact-name/alias entity resolution
- `normalize_evidence.py`: raw FAERS-to-`EvidenceRecord` normalization
- `evidence_schema.py`: evidence integrity and data-origin validation
- `evidence_store.py`: JSON persistence, duplicate detection and conflict audit
- `monitoring.py`: event logging
- `error_handler.py`: application error boundary
- `research_integration.py`: minimum validated-report to source-linked-evidence workflow

## Architecture

```text
validated report
  -> research_integration
  -> OpenFDA REST retrieval
  -> entity resolution
  -> evidence normalization
  -> evidence-schema validation
  -> structured source-linked result
  -> pending human review
```

Existing storage and monitoring components remain available but are not automatically written by the research workflow.

## External boundaries

- Live external integration: OpenFDA drug adverse-event API
- No database service, ML model, Docker deployment, or approved orchestration integration was found
- No verified integration with MASTERDB, MDU, Bucket, TANTRA, SETU, Parikshak, Niyantran, InsightFlow/Pravah or UniGuru/Agent Fabric
