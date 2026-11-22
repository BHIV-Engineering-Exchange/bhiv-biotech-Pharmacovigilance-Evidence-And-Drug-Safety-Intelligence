# Aman Pal — Deployment Readiness

## Local readiness

- Python >=3.10
- Install dependencies: `python -m pip install -r requirements.txt`
- Run tests: `python -m pytest -q`
- Run interactive application: `python app.py`
- Run research workflow through the Python interface in `research_integration.py`

## External prerequisites

- Network access to `https://api.fda.gov`
- No API key or environment variable identified
- No database service identified

## Deployment configuration

- No Dockerfile, compose file or container configuration found
- No service port or health-check route found
- No staging or production configuration found
- No deployment secrets mechanism found

## Verification status

- Local: tested
- Live external source: tested
- Staging: not available
- Production: not deployed

Deployment to a shared or production environment requires authorization and should not claim integration until runtime evidence is independently verified.
