.PHONY: deploy test superadmin token

AWS_PROFILE = codelabs
APP_ENV ?= dev
AWS_REGION ?= sa-east-1
TOKEN_TYPE ?= id

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
