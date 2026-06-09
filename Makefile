.PHONY: bootstrap start setup onboard tui monitor monitor-watch demo-data clean-data index new-experiment verify freeze verify-freeze loop loop-once loop-ui resume test

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

onboard: setup
	$(PY) -m autoresearch.cli onboard

tui: setup
	$(PY) -m autoresearch.cli tui

monitor: setup
	$(PY) -m autoresearch.cli monitor

monitor-watch: setup
	$(PY) -m autoresearch.cli monitor --watch

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

demo-data:
	$(PY) -m autoresearch.prepare_data --write-demo

clean-data:
	$(PY) -m autoresearch.prepare_data

index:
	$(PY) -m autoresearch.cli index

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
	$(PY) -m autoresearch.cli loop

loop-once:
	$(PY) -m autoresearch.cli loop --once

loop-ui:
	$(PY) -m autoresearch.cli loop --ui

resume:
	@if [ -z "$(SESSION)" ]; then echo "usage: make resume SESSION=<codex-session-id>"; exit 2; fi
	$(PY) -m autoresearch.cli loop --resume "$(SESSION)"

test:
	$(PY) -m compileall -q .
	$(PY) -m autoresearch.readme_index --root . --format json >/tmp/autoresearch-index.json
	scripts/verify.sh runs/baseline_classifier/001_baseline
