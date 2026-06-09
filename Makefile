.PHONY: bootstrap start setup demo-data clean-data index new-experiment verify freeze verify-freeze loop test

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	$(PY) -m autoresearch.bootstrap

start: bootstrap

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

demo-data:
	$(PY) -m autoresearch.prepare_data --write-demo

clean-data:
	$(PY) -m autoresearch.prepare_data

index:
	$(PY) -m autoresearch.readme_index --root . --format table

new-experiment:
	$(PY) -m autoresearch.new_experiment

verify:
	@if [ -z "$(RUN)" ]; then echo "usage: make verify RUN=runs/<branch>/<NNN_name>"; exit 2; fi
	scripts/verify.sh "$(RUN)"

freeze:
	$(PY) -m autoresearch.verify_freeze --write

verify-freeze:
	$(PY) -m autoresearch.verify_freeze

loop:
	scripts/agent_loop.sh

test:
	$(PY) -m compileall -q .
	$(PY) -m autoresearch.readme_index --root . --format json >/tmp/autoresearch-index.json
	scripts/verify.sh runs/baseline_classifier/001_baseline
