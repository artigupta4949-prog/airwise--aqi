# AirWise: Urban Air Quality Assistant

## Problem
AQI numbers are abstract, and most tools ignore a household's housing, commute, heating and vulnerable
members. AirWise turns live local air data into a specific exposure-reduction plan, and explains why each
action matters and roughly how much it helps.

## Solution
- Live US AQI and PM2.5 from Open-Meteo (cached 10 min), with a manual AQI fallback.
- A deterministic rule engine (`app/advisor.py`) produces routines, indoor actions and lower-emission alternatives.
  Every action has a title, a reason and an impact.
- Optional Google Gemini (`app/llm.py`) writes a short personal narrative from verified facts only. Without a key,
  or if Gemini fails, the rule-based plan is returned unchanged.

## Architecture
| Module | Responsibility |
|---|---|
| `app/validation.py` | Allow-list parsing of all client input into a frozen `Profile` |
| `app/aqi.py` | EPA categories, gauge position, Open-Meteo lookup with caching |
| `app/advisor.py` | Offline advice engine with named AQI thresholds |
| `app/llm.py` | Gemini narrative; input sanitised, output length-capped, graceful fallback |
| `app/security.py` | Security headers and bounded sliding-window rate limiter |
| `app/errors.py` | JSON error responses for `/api/*` |
| `app/routes.py` | HTTP endpoints (`/`, `/healthz`, `POST /api/advice`) |

## Security
Strict input validation, 8 KB body cap, per-IP rate limiting (proxy-aware via `TRUST_PROXY=1`), CSP with no
inline script/style, HSTS, COOP/CORP, `no-store` on API responses, no `innerHTML`, secrets only via environment,
non-root container, user data treated as data in the LLM prompt.

## Accessibility
Semantic landmarks, skip link, labelled controls with described errors, `aria-live` status, `aria-busy` while loading,
focus moved to results, 44px targets, visible focus, reduced-motion support, `noscript` message, colour never the
only signal.

## Run
```bash
pip install -r requirements-dev.txt
cp .env.example .env      # optional: add GEMINI_API_KEY
python run.py             # http://localhost:5000
```

## Quality checks
```bash
ruff check . && mypy app && pytest   # 75 tests, 100% coverage, CI in .github/workflows/ci.yml
```

## Deploy (Cloud Run)
```bash
gcloud run deploy airwise --source . --region asia-south1 --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-key:latest
```

## Deploy (Vercel)
Import this repository into Vercel. The Flask entry point is declared in `pyproject.toml`;
frontend assets are served from `public/`. `GEMINI_API_KEY` is optional and can be set in
the Vercel project's Environment Variables.
