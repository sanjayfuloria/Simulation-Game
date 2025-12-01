PYTHON ?= python3
# Default to sample env; override with APP_ENV=.env if you create one
APP_ENV ?= .env.example
API_PORT ?= 8000

.PHONY: ui api test fmt lint

ui:
	STREAMLIT_ENV_FILE=$(APP_ENV) streamlit run app/main.py

api:
	UVICORN_ENV_FILE=$(APP_ENV) uvicorn api.main:app --reload --port $(API_PORT)

test:
	$(PYTHON) -m pytest -q

fmt:
	$(PYTHON) -m black app api optimizer tests

lint:
	$(PYTHON) -m ruff app api optimizer tests
