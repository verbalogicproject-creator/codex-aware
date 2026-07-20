.PHONY: api web test typecheck build policy chatgpt

api:
	PYTHONPATH=services/api uvicorn codex_aware.app:app --reload --port 8000

chatgpt:
	PYTHONPATH=services/api uvicorn codex_aware.app:app --reload --port 8001

web:
	cd apps/web && npm run dev

test:
	pytest
	python scripts/check_policy.py examples/team-todo/aware.yaml

typecheck:
	cd apps/web && npm run typecheck

build:
	cd apps/web && npm run build

policy:
	python scripts/check_policy.py examples/team-todo/aware.yaml --require-protected
