.PHONY: install test agent crm

install:
	python -m pip install -e '.[test]'

test:
	python -m pytest -ra

agent:
	uvicorn app.main:app --reload --env-file .env

crm:
	uvicorn app.crm:crm_app --reload --port 8001 --env-file .env
