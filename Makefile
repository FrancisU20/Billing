.PHONY: setup backend-dev backend-test backend-lint frontend-dev frontend-build \
        infra-synth infra-diff deploy-dev migrate help

AWS_PROFILE := codelabs
AWS_REGION  := sa-east-1
ENV         := dev

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Instala todas las dependencias del monorepo
	@echo "→ Backend"
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	@echo "→ Infra"
	cd infra && python -m venv .venv && .venv/bin/pip install -r requirements.txt
	@echo "→ Frontend web"
	cd frontend/web && npm install
	@echo "→ Frontend mobile"
	cd frontend/mobile && npm install
	@echo "→ Frontend shared"
	cd frontend/shared && npm install

backend-dev: ## Levanta la API FastAPI en modo local
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

backend-test: ## Corre tests del backend
	cd backend && .venv/bin/pytest tests/ -v

backend-lint: ## Lint y type check del backend
	cd backend && .venv/bin/ruff check app/ && .venv/bin/mypy app/

frontend-dev: ## Levanta Next.js en modo desarrollo
	cd frontend/web && npm run dev

frontend-build: ## Build de producción del frontend
	cd frontend/web && npm run build

infra-synth: ## CDK synth (sin deploy)
	cd infra && AWS_PROFILE=$(AWS_PROFILE) .venv/bin/cdk synth

infra-diff: ## CDK diff contra el stack desplegado
	cd infra && AWS_PROFILE=$(AWS_PROFILE) .venv/bin/cdk diff

deploy-dev: ## Deploy completo a dev en sa-east-1
	cd infra && AWS_PROFILE=$(AWS_PROFILE) .venv/bin/cdk deploy --all \
		--context env=$(ENV) --require-approval never

migrate: ## Corre migraciones Alembic contra Aurora dev
	cd backend && AWS_PROFILE=$(AWS_PROFILE) .venv/bin/alembic upgrade head

migrate-gen: ## Genera nueva migración Alembic (uso: make migrate-gen msg="descripcion")
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(msg)"
