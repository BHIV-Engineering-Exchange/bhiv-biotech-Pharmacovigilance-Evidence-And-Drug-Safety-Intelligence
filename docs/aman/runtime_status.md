# Aman Pal — Runtime Status

## Environment

- Python: 3.13.5
- Operating system: Windows
- Project requirement: Python >=3.10

## Startup

The repository entry point is:

```powershell
python app.py
```

This is an interactive command-line application. It prompts for a drug name.

## API connectivity

Verified:

```text
python -c "from src.openfda_connector import search_drug; r=search_drug('ibuprofen', limit=1); print(r['success'], r.get('record_count'), r.get('source_url',''))"
```

Result: `success=True`, `record_count=1`.

## Live workflow

Verified:

```text
python -c "from src.research_integration import run_research_workflow; import json; r=run_research_workflow({'report_id':'SYN-LIVE-001','drug_name':'ibuprofen'}, limit=1); print(json.dumps(r, indent=2))"
```

The live result was `REVIEW_REQUIRED` and contained a source-linked `IBUPROFEN` / `Dyspepsia` FAERS record.

## Database and deployment

- No database runtime configured
- No Dockerfile or compose configuration found
- No port or health-check endpoint found
- No deployment configuration or production secret mechanism found
