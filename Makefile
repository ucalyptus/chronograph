PY := python3
PYTHONPATH := src
export PYTHONPATH

.PHONY: help test acceptance unit integration property e2e compile coverage crap boundary dry mutation gherkin_mutation all clean

help:
	@echo "Chronograph quality gate targets (see docs/swarmforge-gates.md for the 11-gate taxonomy):"
	@echo "  test              — unit + integration + property + e2e via unittest discover"
	@echo "  acceptance        — Gherkin scenarios via tests/acceptance_runner.py"
	@echo "  compile           — python -m compileall src tests"
	@echo "  coverage          — coverage run + report + JSON (requires dev deps)"
	@echo "  crap              — scripts/crap.py against coverage/coverage.json"
	@echo "  boundary          — scripts/boundary.py dep-direction check"
	@echo "  dry               — scripts/dry.py duplicate-block check"
	@echo "  mutation          — mutmut run against src/chronograph/{extractor,models}.py (requires dev deps)"
	@echo "  gherkin_mutation  — scripts/soft_gherkin.py mutant scan"
	@echo "  all               — full local quality-gate sweep"

test:
	$(PY) -m unittest discover -s tests -v

acceptance:
	$(PY) tests/acceptance_runner.py

compile:
	$(PY) -m compileall src tests

coverage:
	@mkdir -p coverage
	coverage run --source=src/chronograph -m unittest discover -s tests
	coverage report
	coverage json -o coverage/coverage.json

crap: coverage
	$(PY) scripts/crap.py

boundary:
	$(PY) scripts/boundary.py

dry:
	$(PY) scripts/dry.py

mutation:
	mutmut run

gherkin_mutation:
	$(PY) scripts/soft_gherkin.py

all: compile test acceptance boundary dry coverage crap

clean:
	rm -rf coverage .coverage .mutmut-cache __pycache__ */__pycache__ */*/__pycache__
