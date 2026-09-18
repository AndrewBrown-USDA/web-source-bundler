# Execution Plan 2: Code Review Remediation & Spec Alignment

## Goal & Scope

### Goal
Remediate all issues identified in the two-axis code review against `INITIAL_PROMPT.md` and standard clean-code practices: enforce browser download blocking, unify user agent defaults, align Markdown and header formats to the exact spec while preserving optional helper flags, decouple DOM/AST traversal and clean title extraction duplicates, and eliminate data clumps and untyped accessors.

### In Scope
- **Task 2.1.1 (Security & Capture Config)**: Set `accept_downloads=False` in Playwright context and synchronize default user agent string across `models.py`, `capture.py`, and `cli.py`.
- **Task 2.1.2 (Markdown & Spec Format Alignment)**: Update `build_combined_markdown` to match spec header formatting without bullet points, make `## Index` conditional or spec-aligned, and eliminate `build_readable_markdown` parameter clumps.
- **Task 2.2.1 (AST & DOM Extraction Cleanup)**: Deduplicate fallback title extraction in `extract.py` and modularize DOM/tag traversal logic for `build_ast_document`.
- **Task 2.2.2 (Bundle & Typing Cleanliness)**: Replace untyped `_get_val` in `bundle.py` with typed domain models (`CaptureResult`, `SourceRecord`).
- **Task 2.3.1 (Full Verification & Test Suite Alignment)**: Verify all 70+ unit tests, update test assertions for spec-aligned headers, and verify end-to-end bundling.

### Out of Scope
- Introducing new external libraries or major architectural rewrites.
- Removing useful optional flags (`--redact-pattern`, `--include-links-table`, `--deduplicate`) as decided during grilling.

### Constraints
- Retain 100% test suite passing rate via `python -m pytest`.
- Strictly adhere to `INITIAL_PROMPT.md` formatting contracts.
- Files within each wave must be pairwise-disjoint.

---

## Decision Log
- **2026-09-18**: Keep optional CLI helper features (`--redact-pattern`, `--include-links-table`, URL deduplication) while aligning default header output and combined markdown format to the exact specification.

---

## Wave / Dependency Table

| Wave | Task ID | Description | Target Files | Depends On |
|---|---|---|---|---|
| **Wave 1** | `2.1.1` | Fix browser download blocking & unify User-Agent strings | `source_bundler/capture.py`, `source_bundler/models.py` | None |
| **Wave 1** | `2.1.2` | Align combined/readable markdown formatting & resolve data clumps | `source_bundler/markdown.py` | None |
| **Wave 2** | `2.2.1` | Refactor extract.py: deduplicate title extraction & clean DOM traversal | `source_bundler/extract.py` | None |
| **Wave 2** | `2.2.2` | Refactor bundle.py: replace `_get_val` with typed domain model access | `source_bundler/bundle.py` | `2.1.1`, `2.1.2` |
| **Wave 3** | `2.3.1` | Align unit tests, verify end-to-end test suite and typing | `tests/test_*.py` | `2.1.1`, `2.1.2`, `2.2.1`, `2.2.2` |

---

## Task Specifications

### Task 2.1.1: Fix browser download blocking & unify User-Agent strings
- **ID**: `2.1.1`
- **Files in scope**: `source_bundler/capture.py`, `source_bundler/models.py`
- **Spec Prose**:
  1. In `source_bundler/capture.py`, configure `browser.new_context(accept_downloads=False, ...)` to satisfy spec constraint.
  2. Unify default user agent string across `models.py` and `capture.py` to a single constant (e.g. `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (SourceBundler/0.1.0)`).
- **Grep Anchors**: `browser.new_context`, `DEFAULT_USER_AGENT`, `CaptureConfig.user_agent`
- **Acceptance Command**: `python -m pytest tests/test_capture.py`

### Task 2.1.2: Align combined/readable markdown formatting & resolve data clumps
- **ID**: `2.1.2`
- **Files in scope**: `source_bundler/markdown.py`
- **Spec Prose**:
  1. Update `build_combined_markdown` header metadata format to match spec exact format:
     ```markdown
     # Source Bundle

     Bundle ID: {bundle_id}  
     Created: {created_at}  
     Tool: {tool_name} {tool_version}

     Use this document as the reference source bundle. Cite material by source ID.
     ```
  2. Make the index table only appear if requested or ensure default matches spec.
  3. Bundle loose parameters in `build_readable_markdown` into a structured source context or typed helper to eliminate the 10-parameter clump.
- **Grep Anchors**: `def build_combined_markdown`, `def build_readable_markdown`
- **Acceptance Command**: `python -m pytest tests/test_markdown.py`

### Task 2.2.1: Refactor extract.py: deduplicate title extraction & clean DOM traversal
- **ID**: `2.2.1`
- **Files in scope**: `source_bundler/extract.py`
- **Spec Prose**:
  1. Extract a single helper `_extract_page_title(soup: BeautifulSoup) -> str` to deduplicate title extraction logic between initial parsing and readability cleanup.
  2. Clean up `_ast_for_tag` and DOM node inspection in `build_ast_document` into clean, modular helper functions.
- **Grep Anchors**: `def _extract_title`, `def _ast_for_tag`, `def build_ast_document`
- **Acceptance Command**: `python -m pytest tests/test_extract.py`

### Task 2.2.2: Refactor bundle.py: replace `_get_val` with typed domain model access
- **ID**: `2.2.2`
- **Files in scope**: `source_bundler/bundle.py`
- **Spec Prose**:
  1. Replace untyped `_get_val` helper and loose dict accesses in `BundlePackager` with typed `CaptureResult` and `SourceRecord` model accesses.
  2. Ensure all calls into `build_readable_markdown` pass typed source records cleanly.
- **Grep Anchors**: `def _get_val`, `def add_source`
- **Acceptance Command**: `python -m pytest tests/test_bundle.py`

### Task 2.3.1: Align unit tests, verify end-to-end test suite and typing
- **ID**: `2.3.1`
- **Files in scope**: `tests/test_markdown.py`, `tests/test_bundle.py`, `tests/test_capture.py`, `tests/test_cli.py`
- **Spec Prose**:
  1. Update test assertions in `tests/test_markdown.py` and `tests/test_bundle.py` to match the spec-aligned header and markdown output.
  2. Run the complete test suite to ensure all unit tests pass cleanly.
- **Grep Anchors**: `def test_build_combined_markdown`, `def test_bundle_packager`
- **Acceptance Command**: `python -m pytest`
