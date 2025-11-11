ifneq (,$(wildcard .env))
include .env
export GEMINI_API_KEY FILE_SEARCH_STORE_NAME PDF_FOLDER PDF_STORE_DISPLAY_NAME
endif

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

DEFAULT_STORE_NAME := $(FILE_SEARCH_STORE_NAME)
DEFAULT_PDF_FOLDER := $(PDF_FOLDER)
DEFAULT_PDF_STORE_DISPLAY_NAME := $(PDF_STORE_DISPLAY_NAME)

.PHONY: setup ingest_pdfs query

setup:
	@[ -d $(VENV) ] || python3 -m venv $(VENV)
	@$(PIP) install -r requirements.txt

ingest_pdfs:
	@FOLDER="$${FOLDER:-$(DEFAULT_PDF_FOLDER)}"; \
	STORE_DISPLAY_NAME="$${STORE_DISPLAY_NAME:-$(DEFAULT_PDF_STORE_DISPLAY_NAME)}"; \
	STORE_NAME="$${STORE_NAME:-$(DEFAULT_STORE_NAME)}"; \
	CMD="$(PYTHON) ingest_pdfs.py \"$$FOLDER\" --store-display-name \"$$STORE_DISPLAY_NAME\""; \
	if [ -n "$$STORE_NAME" ]; then \
		CMD="$$CMD --store-name \"$$STORE_NAME\""; \
	fi; \
	eval "$$CMD"

query:
	@QUESTION="$(QUESTION)"; \
	STORE_NAME="$${STORE_NAME:-$(DEFAULT_STORE_NAME)}"; \
	if [ -z "$$QUESTION" ]; then \
		echo "Set QUESTION=... when calling make query"; \
		exit 1; \
	fi; \
	if [ -z "$$STORE_NAME" ]; then \
		echo "Set FILE_SEARCH_STORE_NAME in .env or pass STORE_NAME=..."; \
		exit 1; \
	fi; \
	CMD="$(PYTHON) query.py \"$$QUESTION\" --store-name \"$$STORE_NAME\""; \
	if [ -n "$$SOURCE_TYPE" ]; then \
		CMD="$$CMD --source-type \"$$SOURCE_TYPE\""; \
	fi; \
	eval "$$CMD"
