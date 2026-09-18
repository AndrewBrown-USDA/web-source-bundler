# Source Bundler — Makefile
# Core development workflows

.PHONY: help install dev-install test test-cov run-capture run-bundle clean

.DEFAULT_GOAL := help

PYTHON ?= python

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install package in editable mode
	$(PYTHON) -m pip install -e .

dev-install: ## Install package with dev dependencies and Playwright browsers
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m playwright install --with-deps chromium

test: ## Run unit and integration tests
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Run tests with coverage summary (if pytest-cov installed)
	$(PYTHON) -m pytest tests/ --cov=source_bundler -v

run-capture: ## Run CLI capture command (usage: make run-capture URL=https://example.com)
	$(PYTHON) -m source_bundler.cli capture $(URL)

run-bundle: ## Run CLI bundle command (usage: make run-bundle BUNDLE_DIR=./bundle_dir)
	$(PYTHON) -m source_bundler.cli bundle $(BUNDLE_DIR)

clean: ## Clean build, test, and python bytecode artifacts
	@python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink() for p in pathlib.Path('.').rglob('*.py[cod]')]; [shutil.rmtree(p, ignore_errors=True) for p in [pathlib.Path('build'), pathlib.Path('dist'), pathlib.Path('.pytest_cache'), pathlib.Path('htmlcov')]]"
	@echo "Clean completed."
