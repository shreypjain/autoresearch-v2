.PHONY: bootstrap start setup onboard tui monitor monitor-watch demo-data clean-data index new-experiment verify freeze verify-freeze loop loop-once loop-ui resume test

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
INSTALL_STAMP := $(VENV)/.autoresearch-installed
SRC_PATH := $(CURDIR)/src
RUN_PY := PYTHONPATH=$(SRC_PATH) $(PY)

bootstrap: setup
	$(RUN_PY) -m autoresearch.bootstrap

$(PY):
	$(PYTHON) -m venv $(VENV)

$(INSTALL_STAMP): pyproject.toml | $(PY)
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	@touch $(INSTALL_STAMP)

start: bootstrap

onboard: setup
	$(RUN_PY) -m autoresearch.cli onboard

tui: setup
	$(RUN_PY) -m autoresearch.cli tui

monitor: setup
	$(RUN_PY) -m autoresearch.cli monitor

monitor-watch: setup
	$(RUN_PY) -m autoresearch.cli monitor --watch

setup: $(INSTALL_STAMP)
	@$(RUN_PY) -c "import autoresearch" 2>/dev/null || { rm -f $(INSTALL_STAMP); $(MAKE) $(INSTALL_STAMP); }

demo-data:
	$(RUN_PY) -m autoresearch.prepare_data --write-demo

clean-data:
	$(RUN_PY) -m autoresearch.prepare_data

index:
	$(RUN_PY) -m autoresearch.cli index

new-experiment:
	$(RUN_PY) -m autoresearch.new_experiment

verify:
	@if [ -z "$(RUN)" ]; then echo "usage: make verify RUN=runs/<branch>/<NNN_name>"; exit 2; fi
	scripts/verify.sh "$(RUN)"

freeze:
	$(RUN_PY) -m autoresearch.verify_freeze --write

verify-freeze:
	$(RUN_PY) -m autoresearch.verify_freeze

loop:
	$(RUN_PY) -m autoresearch.cli loop

loop-once:
	$(RUN_PY) -m autoresearch.cli loop --once

loop-ui:
	$(RUN_PY) -m autoresearch.cli loop --ui

resume:
	@if [ -z "$(SESSION)" ]; then echo "usage: make resume SESSION=<codex-session-id>"; exit 2; fi
	$(RUN_PY) -m autoresearch.cli loop --resume "$(SESSION)"

test:
	$(RUN_PY) -m compileall -q .
	$(RUN_PY) -m autoresearch.readme_index --root . --format json >/tmp/autoresearch-index.json
	scripts/verify.sh runs/baseline_classifier/001_baseline
