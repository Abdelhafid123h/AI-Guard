AI-Guards (MySQL-first)

Overview
- FastAPI backend (port 8000) + React frontend (port 3000) + MySQL 8 (port 3307 host).
- Backend prefers MySQL; will fall back to SQLite only if you change DB_ENGINE.
- Default guard types are seeded idempotently at startup: InfoPerso, TypeA, TypeB.

Setup (.env)
- Copy the template and fill your values locally (do not commit .env):
	- Windows PowerShell:
		- Copy-Item .env.example .env
	- Set at least OPENAI_API_KEY and (optionally) MySQL values.
- .env is git-ignored; commit only .env.example.

Quick start
1) Prerequisites
- Docker Desktop installed and running
- Create .env from the example (see Setup above) and set at least:
	- OPENAI_API_KEY=sk-...
	- MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD (optional if you keep defaults in compose)

2) Start the stack (from repo root)

	docker compose build --no-cache
	docker compose up -d

3) Open the app
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Key endpoints
- POST /process: Process text with masking based on guard_type
- GET /api/config/guard-types: List guard types
- GET /api/config/regex-patterns: List regex patterns
- GET /usage/history: Last runs with token_in/out and masked_token_count

Notes
- Healthcheck is internal (Python urlopen), no curl dependency in the image.
- On first start, backend waits for MySQL and seeds defaults.
- Confidence/priority fields were removed from the public API.

Troubleshooting
- Backend “health: starting” for long:
	- Check MySQL container is healthy (docker compose ps)
	- View backend logs: docker compose logs ai-guards-backend --tail=200
	- Stream logs live: docker compose logs -f ai-guards-backend
	- Ensure the DB user exists and can connect from the backend:
		- MySQL runs inside docker; user ai_guards/ai_guards_pwd on DB ai_guards is created by env.
	- If you changed creds, update .env and docker-compose, then redeploy.
- Frontend cannot reach backend:
	- Backend must be on http://localhost:8000; React uses REACT_APP_API_URL env.

LLM setup
- Ensure OPENAI_API_KEY is set in .env before starting containers.
- We don’t override OPENAI_API_KEY in compose; it’s taken from .env via env_file.
- On startup you should see: "✅ OPENAI_API_KEY chargé" in backend logs if detected.

NER accuracy (FR)
- Presidio + spaCy models are installed (fr_core_news_sm, en_core_web_sm).
- To improve recall for person names (risking more false positives), set PII_HIGH_RECALL_PERSON=1 in .env.
- You can limit/analyse languages via PII_PRESIDIO_LANGS=fr,en.
- Backend logs print detected model list and Presidio supported entities.

Secrets & persistence
- Never commit .env; it’s already in .gitignore. Commit .env.example only.
- To keep data, do not run docker-compose down -v (the -v deletes volumes including MySQL data).
- MySQL data persists in volume ai-guards_mysql_data; logs persist in ai-guards_ai_guards_logs.

Dev tips
- Code is under backend/app and frontend/src.
- To modify backend, edit files and restart that service: docker-compose restart ai-guards-backend
- To view usage columns and last row: GET http://localhost:8000/usage/debug
