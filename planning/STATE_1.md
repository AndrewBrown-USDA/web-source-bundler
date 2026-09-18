# Orchestration State: Plan 1

## Baseline Status
- **Repository**: `source-bundler` (fresh workspace)
- **Target Version**: `0.1.0`
- **Python Version**: `3.14+`
- **Initial Baseline**: Clean working directory, 0 tests

---

## Wave Board

### Wave 1
- [x] `T1.1-scaffold-and-models` (done) — Package scaffold, `pyproject.toml`, Pydantic models
- [x] `T1.2-utils-and-hashing` (done) — Sanitization, timestamp utilities, SHA-256 hashing

### Wave 2
- [ ] `T2.1-selection-and-inputs` (pending) — Input parsing, interactive selection, deduplication
- [ ] `T2.2-extract-and-ast` (pending) — HTML content cleaning, readability, block-level AST
- [ ] `T2.3-markdown-and-redact` (pending) — Front matter, readable.md, combined.md, redaction, links table

### Wave 3
- [ ] `T3.1-playwright-capture` (pending) — Headless Chromium capture, screenshot, PDF, headers
- [ ] `T3.2-bundle-packager` (pending) — Bundle assembly, manifest writer, checksum generator

### Wave 4
- [ ] `T4.1-cli-interface` (pending) — Typer CLI commands (`urls`, `file`, `search-results`), Rich UX
- [ ] `T4.2-docs-and-validation` (pending) — README.md, end-to-end acceptance validation

---

## Task Reports

### T1.1-scaffold-and-models
- Status: completed
- Files: `pyproject.toml`, `source_bundler/__init__.py`, `source_bundler/models.py`
- Test: `python -c "import source_bundler; from source_bundler.models import Manifest, ASTDocument, SourceRecord; print('Models OK')"` -> Models OK
- Deviations: none

### T1.2-utils-and-hashing
- Status: completed
- Files: `source_bundler/utils.py`, `source_bundler/hashing.py`, `tests/test_utils.py`, `tests/test_hashing.py`
- Test: `python -m pytest tests/test_utils.py tests/test_hashing.py -v` -> 21 passed
- Deviations: none

