.PHONY: deploy test superadmin token \
        ci ci-backend ci-security ci-frontend ci-cdk

AWS_PROFILE = codelabs
APP_ENV ?= dev
AWS_REGION ?= sa-east-1
TOKEN_TYPE ?= id

# ── CI local — espejo exacto de pr-checks.yml ──────────────────────────────
# Corre ANTES de cualquier push. Si falla aqui, fallara en CI.
# Prerequisito: backend/.venv instalado con requirements.txt + requirements-ci.txt
#               (ver CLAUDE.md > Antes de hacer push)

ci: ci-backend ci-security ci-frontend ci-cdk

ci-backend:
	@echo "==> Backend: lint & format"
	backend/.venv/bin/ruff format --check backend/
	backend/.venv/bin/ruff check backend/
	@echo "==> Backend: unit tests + coverage"
	PYTHONPATH=backend backend/.venv/bin/coverage run \
		--source=lambdas,shared \
		-m unittest discover -s backend/tests -p "test_*.py"
	PYTHONPATH=backend backend/.venv/bin/coverage report

ci-security:
	@echo "==> Security: bandit (SAST)"
	backend/.venv/bin/bandit -r backend/lambdas/ backend/shared/ \
		-c backend/pyproject.toml --severity-level medium
	@echo "==> Security: pip-audit (dependencias)"
	backend/.venv/bin/pip-audit -r backend/requirements.txt --strict

ci-frontend:
	@echo "==> Frontend: format + lint + typecheck + tests"
	cd frontend && npm run format:check
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run test:run

ci-cdk:
	@echo "==> CDK: validar que los stacks compilan"
	cd infra && source .venv/bin/activate && cdk ls -c env=dev

# ── Helpers ────────────────────────────────────────────────────────────────

deploy:
	cd infra && source .venv/bin/activate && \
		cdk deploy --all --profile $(AWS_PROFILE) --require-approval never

test:
	PYTHONPATH=backend backend/.venv/bin/python -m unittest discover \
		-s backend/tests -p 'test_*.py'

superadmin:
	AWS_PROFILE=$(AWS_PROFILE) AWS_REGION=$(AWS_REGION) ENV=$(APP_ENV) \
		backend/.venv/bin/python scripts/create_superadmin.py

token:
	AWS_PROFILE=$(AWS_PROFILE) AWS_REGION=$(AWS_REGION) ENV=$(APP_ENV) \
		TOKEN_TYPE=$(TOKEN_TYPE) backend/.venv/bin/python scripts/make_token.py
