.PHONY: deploy run test

AWS_PROFILE = codelabs

deploy:
	cd infra && source .venv/bin/activate && \
		cdk deploy --all --profile $(AWS_PROFILE) --require-approval never

run:
	cd local && AWS_PROFILE=$(AWS_PROFILE) PYTHONPATH=../backend:. \
		../backend/.venv/bin/python server.py

test:
	PYTHONPATH=backend:local backend/.venv/bin/python -m unittest discover \
		-s backend/tests -p 'test_*.py'
