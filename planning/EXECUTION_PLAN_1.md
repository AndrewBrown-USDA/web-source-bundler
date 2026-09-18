# Execution Plan: source-bundler (Plan 1)

## Goal & Scope

### Goal
Build `source-bundler`, a deterministic local Python CLI tool that captures web sources for AI-assisted research workflows. It accepts direct URLs, plain URL text files, or search-results JSON files; provides optional interactive selection; renders selected pages with headless Chromium via Playwright; extracts readable content into structured block-level AST JSON and clean Markdown with YAML front matter; hashes all artifacts with SHA-256; and outputs an upload-ready source bundle containing `manifest.json`, `combined.md`, `checksums.sha256`, and per-source archival artifacts (`metadata.json`, `rendered.html`, `readable.md`, `ast.json`, `screenshot.png`, `page.pdf`, and optional raw headers/HTML).

### In Scope
1. **Core Data Models & Schemas** (`source_bundler/models.py`):
   - Pydantic v2 models for `Manifest`, `SourceMetadata`, `ArtifactRefs`, `SourceHashes`, `SourceError`, `CaptureConfig`, `ASTDocument`, `ASTBlock`, `SearchResultItem`.
   - Serialization to/from JSON with ISO 8601 UTC timestamps.
2. **Utilities & Hashing** (`source_bundler/utils.py`, `source_bundler/hashing.py`):
   - Path/filename sanitization (slugifying URLs/titles, preventing directory traversal).
   - Timestamp utilities (UTC ISO 8601 format: `YYYYMMDDTHHMMSSZ` and `YYYY-MM-DDTHH:MM:SSZ`).
   - SHA-256 file and string hashing routines, `checksums.sha256` generation in standard format (`<hex>  <relative-path>`).
3. **Input Parsing & Selection** (`source_bundler/selection.py`):
   - Plain URL file parser (ignoring blank lines and comments `#`).
   - Search results JSON parser (supporting `title`, `url` / `link`, `snippet`).
   - Interactive CLI selection prompt (`[Y/n]`, default `Y`, tracking selection decisions).
   - URL normalization and deduplication by final/canonical URL.
4. **Content Extraction & AST Generation** (`source_bundler/extract.py`):
   - HTML sanitization and boilerplate removal (`script`, `style`, `noscript`, `svg`, `canvas`, `nav`, `footer`, cookie banners).
   - Main content targeting (`main`, `article`, `[role="main"]`, `body`).
   - Structural AST generation (`ast.json`) with block types (`heading`, `paragraph`, `list`, `blockquote`, `code_block`, `table`, `link`).
5. **Markdown Generation & Redaction** (`source_bundler/markdown.py`):
   - Single source `readable.md` generation with YAML front matter.
   - Consolidated `combined.md` generation with bundle header, index, and formatted per-source content with error notices.
   - Optional `--redact-pattern <REGEX>` scrubbing (replacing matching patterns with `[REDACTED]`).
   - Optional `--include-links-table` appending extracted links table.
6. **Playwright Browser Capture** (`source_bundler/capture.py`):
   - Headless Chromium with deterministic configuration (viewport 1365x768, locale `en-US`, timezone `UTC`, fixed desktop User-Agent).
   - Isolated browser context per run (no cookie persistence, no service workers, no credential storage, downloads disabled).
   - Capture steps: `domcontentloaded` navigation, short network-idle delay, full-page screenshot (`screenshot.png`), PDF printout (`page.pdf`), rendered HTML (`rendered.html`), page title, final URL, HTTP status/headers, optional raw response HTML (`raw.html`).
   - Non-fatal per-source error trapping and logging to metadata.
7. **Bundle Packaging & Orchestration** (`source_bundler/bundle.py`):
   - Output directory management (`source-bundle-YYYYMMDDTHHMMSSZ` or custom `--out`).
   - Per-source directory structure (`sources/001/`, `sources/002/`).
   - Writing `manifest.json`, `combined.md`, `checksums.sha256`, and per-source artifact trees.
8. **CLI Interface & Entry Points** (`source_bundler/cli.py`, `pyproject.toml`):
   - Typer CLI with commands: `urls`, `file`, `search-results`.
   - CLI flags: `--out`, `--interactive`, `--no-pdf`, `--no-screenshot`, `--include-raw-html`, `--redact-pattern`, `--include-links-table`, `--timeout`, `--concurrency`.
   - Packaging config with `hatchling`, console script entry point `source-bundler = "source_bundler.cli:app"`.
9. **Documentation & Unit Tests** (`README.md`, `tests/`):
   - Unit tests with `pytest` for parsing, sanitization, hashing, markdown generation, AST extraction, and mocking capture.
   - Comprehensive README covering installation, Playwright setup, usage examples, architecture, provenance/records review, and security/copyright notes.

### Out of Scope (Deferred to post-v0.1.0)
- WARC export (`--format warc`).
- Recursive web crawling (`--depth 1`, `--same-domain-only`, `--max-pages`).
- Direct search engine query API integration (`--query`).
- Interactive web UI / local HTML dashboard for bundle inspection.

### Verbatim Constraints
- "Implement in Python."
- "Use Playwright for browser rendering."
- "Prefer deterministic behavior: fixed viewport, fixed user agent, fixed timezone if possible, fixed locale, configurable timeout, no persistent browser profile by default, disable service workers if possible, do not reuse cookies unless explicitly requested."
- "Do not execute shell commands on page content."
- "Sanitize filenames derived from URLs."
- "Do not upload anything automatically. This is a local capture and packaging tool only."
- "Do not bypass paywalls, authentication, robots restrictions, or access controls."
- "Clearly mark failures in the manifest instead of silently skipping them."

---

## Decision Log

1. **2026-09-18 — CLI & Data Models**: Typer + Rich for CLI interface; Pydantic v2 for data schemas and JSON serialization; `hatchling` as build backend in `pyproject.toml`.
2. **2026-09-18 — Extraction Pipeline**: `readability-lxml` / `beautifulsoup4` + `markdownify` for content extraction; structural block-level `ast.json` generated for every source.
3. **2026-09-18 — Secondary Features for v0.1.0**: URL deduplication, optional `--include-links-table`, optional `--include-raw-html`, and optional `--redact-pattern` included in v0.1.0.
4. **2026-09-18 — Execution & Models**: Worker and escalation model set to `gemini-3.7-flash`; max concurrent workers set to 3.

---

## Codebase Reconnaissance & Hazards

- **Repo state**: Fresh repository initialized with `planning/INITIAL_PROMPT.md`. Python 3.14+ installed.
- **Dependency isolation**: Package must install cleanly with `pip install -e .` or `uv pip install -e .`.
- **Playwright offline testing hazard**: Unit tests must not require live network access; Playwright interactions should be abstracted/mocked in unit tests.
- **Path separators hazard**: Must use `pathlib.Path` with posix-style relative paths in `manifest.json` and `checksums.sha256` for cross-platform portability across Windows and Linux.

---

## Wave Dependency Table

| Wave | Task ID | Description | Dependencies | Files in Scope |
|---|---|---|---|---|
| **Wave 1** | `T1.1-scaffold-and-models` | Package scaffold, `pyproject.toml`, and Pydantic v2 models | None | `pyproject.toml`, `source_bundler/__init__.py`, `source_bundler/models.py` |
| **Wave 1** | `T1.2-utils-and-hashing` | Path sanitization, timestamp utils, and SHA-256 hashing | None | `source_bundler/utils.py`, `source_bundler/hashing.py`, `tests/test_utils.py`, `tests/test_hashing.py` |
| **Wave 2** | `T2.1-selection-and-inputs` | Input parsing (file, JSON), interactive selector, and deduplication | `T1.1`, `T1.2` | `source_bundler/selection.py`, `tests/test_selection.py` |
| **Wave 2** | `T2.2-extract-and-ast` | HTML content extraction, cleaning, and block-level AST generation | `T1.1`, `T1.2` | `source_bundler/extract.py`, `tests/test_extract.py` |
| **Wave 2** | `T2.3-markdown-and-redact` | Readable Markdown with YAML front matter, combined.md, links table, and redaction | `T1.1`, `T1.2` | `source_bundler/markdown.py`, `tests/test_markdown.py` |
| **Wave 3** | `T3.1-playwright-capture` | Deterministic Playwright capture (DOM, screenshot, PDF, headers, error trap) | `T1.1`, `T1.2` | `source_bundler/capture.py`, `tests/test_capture.py` |
| **Wave 3** | `T3.2-bundle-packager` | Bundle directory assembly, manifest generation, and checksum writer | `T1.1`, `T1.2`, `T2.2`, `T2.3` | `source_bundler/bundle.py`, `tests/test_bundle.py` |
| **Wave 4** | `T4.1-cli-interface` | Typer CLI commands (`urls`, `file`, `search-results`) & rich output | `T2.1`, `T3.1`, `T3.2` | `source_bundler/cli.py`, `tests/test_cli.py` |
| **Wave 4** | `T4.2-docs-and-validation` | Comprehensive README.md and full end-to-end acceptance validation | `T4.1` | `README.md` |

---

## Task Specifications

### Wave 1

#### `T1.1-scaffold-and-models`
- **Repo**: `source-bundler`
- **Depends on**: None
- **Files in scope**: `pyproject.toml`, `source_bundler/__init__.py`, `source_bundler/models.py`
- **Constraints**: Do not touch `utils.py` or `hashing.py`. Use Pydantic v2.
- **Spec**:
  1. Create `pyproject.toml` with `hatchling` build-backend, metadata, dependencies (`typer>=0.9.0`, `rich>=13.0.0`, `pydantic>=2.0.0`, `playwright>=1.40.0`, `beautifulsoup4>=4.12.0`, `markdownify>=0.11.0`, `readability-lxml>=0.8.1`, `lxml>=4.9.0`, `python-slugify>=8.0.0`), dev dependencies (`pytest>=8.0.0`), and console script `source-bundler = "source_bundler.cli:app"`.
  2. Create `source_bundler/__init__.py` with `__version__ = "0.1.0"`.
  3. Create `source_bundler/models.py` with Pydantic models:
     - `CaptureConfig`: viewport (width, height), locale, timezone, user_agent, timeout_seconds.
     - `ToolInfo`: name, version.
     - `SourceError`: stage (str), message (str), timestamp (datetime).
     - `ArtifactRefs`: rendered_html, readable_markdown, ast_json, screenshot, pdf, response_headers, raw_html (all Optional[str]).
     - `SourceHashes`: dict of artifact_key -> sha256_hash.
     - `SourceRecord`: source_id, input_url, final_url, title, selected, selection_note, fetched_at, http_status, content_type, artifacts, hashes, errors.
     - `Manifest`: bundle_id, created_at, tool, capture_config, sources.
     - `ASTBlock`: type (`heading`, `paragraph`, `list`, `blockquote`, `code_block`, `table`, `link`), level, text, href, items, rows, extra fields.
     - `ASTDocument`: source_id, title, final_url, blocks.
     - `SearchResultItem`: title, url, snippet.
- **Acceptance command**: `python -c "import source_bundler; from source_bundler.models import Manifest, ASTDocument, SourceRecord; print('Models OK')"`

#### `T1.2-utils-and-hashing`
- **Repo**: `source-bundler`
- **Depends on**: None
- **Files in scope**: `source_bundler/utils.py`, `source_bundler/hashing.py`, `tests/test_utils.py`, `tests/test_hashing.py`
- **Constraints**: Do not touch `models.py`.
- **Spec**:
  1. `source_bundler/utils.py`:
     - `sanitize_filename(name: str, max_length: int = 100) -> str`: safe alphanumeric + dash/underscore slug.
     - `format_utc_timestamp(dt: Optional[datetime] = None) -> str`: returns ISO 8601 string `YYYY-MM-DDTHH:MM:SSZ`.
     - `generate_bundle_id(dt: Optional[datetime] = None) -> str`: returns `source-bundle-YYYYMMDDTHHMMSSZ`.
     - `normalize_url(url: str) -> str`: trims whitespace, normalizes scheme/casing/trailing slashes.
  2. `source_bundler/hashing.py`:
     - `hash_bytes(data: bytes) -> str`: returns `sha256:<hex>`.
     - `hash_file(path: Union[str, Path]) -> str`: streaming SHA-256 for large files, returns `sha256:<hex>`.
     - `hash_string(text: str) -> str`: SHA-256 of UTF-8 string, returns `sha256:<hex>`.
     - `generate_checksums_content(file_hash_map: Dict[str, str]) -> str`: standard `<hex>  <posix_relpath>\n` format (stripping `sha256:` prefix for checksums file compatibility).
  3. Write unit tests in `tests/test_utils.py` and `tests/test_hashing.py`.
- **Acceptance command**: `pytest tests/test_utils.py tests/test_hashing.py -v`

---

### Wave 2

#### `T2.1-selection-and-inputs`
- **Repo**: `source-bundler`
- **Depends on**: `T1.1-scaffold-and-models`, `T1.2-utils-and-hashing`
- **Files in scope**: `source_bundler/selection.py`, `tests/test_selection.py`
- **Constraints**: Do not touch `extract.py` or `markdown.py`.
- **Spec**:
  1. `parse_url_file(file_path: Path) -> List[SearchResultItem]`: Reads plain text, ignores empty lines and `#` comments, wraps into `SearchResultItem(url=..., title=None, snippet=None)`.
  2. `parse_search_json(file_path: Path) -> List[SearchResultItem]`: Reads JSON array, handles `url` or `link` alias, `title`, `snippet`.
  3. `deduplicate_items(items: List[SearchResultItem]) -> List[SearchResultItem]`: Deduplicates items by normalized URL while preserving first-seen order.
  4. `select_sources_interactively(items: List[SearchResultItem], prompt_func=None) -> List[Tuple[SearchResultItem, bool, Optional[str]]]`:
     - Presents each candidate `[i] Title\n  URL\n  Snippet\n Include this source? [Y/n]:`.
     - Default is yes (`True`).
     - Returns tuple of item, selected boolean, and selection note.
  5. Write unit tests in `tests/test_selection.py`.
- **Acceptance command**: `pytest tests/test_selection.py -v`

#### `T2.2-extract-and-ast`
- **Repo**: `source-bundler`
- **Depends on**: `T1.1-scaffold-and-models`, `T1.2-utils-and-hashing`
- **Files in scope**: `source_bundler/extract.py`, `tests/test_extract.py`
- **Constraints**: Do not touch `selection.py` or `markdown.py`.
- **Spec**:
  1. `extract_readable_html(raw_html: str, url: Optional[str] = None) -> Tuple[str, str]`:
     - Uses `readability-lxml` (or BeautifulSoup fallback) to extract main title and main article/body HTML.
     - Strips unwanted tags: `script`, `style`, `noscript`, `svg`, `canvas`, `nav`, `footer`, cookie banner selectors.
     - Retains semantic HTML: headings (`h1`-`h6`), `p`, `ul`, `ol`, `li`, `blockquote`, `pre`, `code`, `table`, `a`.
  2. `build_ast_document(source_id: str, title: str, final_url: str, cleaned_html: str) -> ASTDocument`:
     - Parses cleaned HTML into structured blocks (`heading` with level, `paragraph`, `list` ordered/unordered with items, `blockquote`, `code_block` with language/code, `table` with headers/rows, `link` with text/href).
     - Returns `ASTDocument` instance.
  3. Write unit tests in `tests/test_extract.py` testing against sample HTML snippets.
- **Acceptance command**: `pytest tests/test_extract.py -v`

#### `T2.3-markdown-and-redact`
- **Repo**: `source-bundler`
- **Depends on**: `T1.1-scaffold-and-models`, `T1.2-utils-and-hashing`
- **Files in scope**: `source_bundler/markdown.py`, `tests/test_markdown.py`
- **Constraints**: Do not touch `selection.py` or `extract.py`.
- **Spec**:
  1. `html_to_markdown(html_content: str, strip_tags: Optional[List[str]] = None) -> str`:
     - Converts cleaned HTML to clean standard Markdown using `markdownify` or BeautifulSoup formatting.
     - Preserves headings, lists, tables, code blocks, links.
  2. `apply_redactions(text: str, patterns: Optional[List[str]]) -> str`:
     - If patterns are provided, compiles regexes and substitutes matches with `[REDACTED]`.
  3. `build_readable_markdown(source_id: str, title: str, input_url: str, final_url: str, fetched_at: str, http_status: Optional[int], content_md: str, extracted_links: Optional[List[Tuple[str, str]]] = None, include_links_table: bool = False, redact_patterns: Optional[List[str]] = None) -> str`:
     - Generates YAML front matter header (`source_id`, `title`, `input_url`, `final_url`, `fetched_at`, `http_status`).
     - Appends redacted markdown content.
     - If `include_links_table` is True, appends a Markdown table of extracted `[Text, URL]`.
  4. `build_combined_markdown(manifest: Manifest, source_markdowns: Dict[str, str]) -> str`:
     - Header: `# Source Bundle`, Bundle ID, Created, Tool.
     - Usage prompt instructions ("Use this document as reference... Cite material by source ID.").
     - Index section listing sources with status/hashes.
     - Per-source sections (`## Source 001: <Title>`, Input URL, Final URL, Fetched, SHA-256, `### Content`, body or error notice).
  5. Write unit tests in `tests/test_markdown.py`.
- **Acceptance command**: `pytest tests/test_markdown.py -v`

---

### Wave 3

#### `T3.1-playwright-capture`
- **Repo**: `source-bundler`
- **Depends on**: `T1.1-scaffold-and-models`, `T1.2-utils-and-hashing`
- **Files in scope**: `source_bundler/capture.py`, `tests/test_capture.py`
- **Constraints**: Do not touch `bundle.py`.
- **Spec**:
  1. Define deterministic capture defaults:
     - Viewport: `{"width": 1365, "height": 768}`
     - Locale: `en-US`
     - Timezone: `UTC`
     - Stable desktop User-Agent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 SourceBundler/0.1.0`
     - Service workers disabled (`service_workers="block"` or equivalent context option).
     - No cookie persistence between runs.
  2. `async def capture_url(url: str, config: CaptureConfig, save_screenshot: bool = True, save_pdf: bool = True, save_raw_html: bool = False) -> CaptureResult`:
     - `CaptureResult` dataclass: `final_url`, `title`, `http_status`, `content_type`, `rendered_html`, `raw_html`, `screenshot_bytes`, `pdf_bytes`, `response_headers`, `errors: List[SourceError]`.
     - Navigates with `page.goto(url, wait_until="domcontentloaded", timeout=config.timeout_seconds * 1000)`.
     - Waits for network idle with short fallback timeout (e.g. 3s).
     - Extracts title, content, response headers, full-page screenshot bytes, PDF print bytes.
     - Catches navigation errors (TimeoutError, net::ERR_NAME_NOT_RESOLVED) without throwing, populates `errors` list.
  3. `def run_capture(...) -> CaptureResult`: Synchronous / asyncio wrapper.
  4. Mocked unit tests in `tests/test_capture.py` verifying error trapping and configuration propagation.
- **Acceptance command**: `pytest tests/test_capture.py -v`

#### `T3.2-bundle-packager`
- **Repo**: `source-bundler`
- **Depends on**: `T1.1-scaffold-and-models`, `T1.2-utils-and-hashing`, `T2.2-extract-and-ast`, `T2.3-markdown-and-redact`
- **Files in scope**: `source_bundler/bundle.py`, `tests/test_bundle.py`
- **Constraints**: Do not touch `capture.py`.
- **Spec**:
  1. `class BundlePackager`:
     - Initializes target directory `source-bundle-YYYYMMDDTHHMMSSZ` (or custom `--out`).
     - Manages per-source directories `sources/001/`, `sources/002/`.
     - For each source: writes `rendered.html`, `readable.md`, `ast.json`, `screenshot.png` (if present), `page.pdf` (if present), `metadata.json`, optional `response_headers.json`, `raw.html`.
     - Computes SHA-256 for all generated files using `hashing.py`.
     - Generates and writes `manifest.json`.
     - Generates and writes `combined.md`.
     - Generates and writes `checksums.sha256` containing relative paths of all bundle files.
  2. Write unit tests in `tests/test_bundle.py` using temporary directories (`tmp_path`).
- **Acceptance command**: `pytest tests/test_bundle.py -v`

---

### Wave 4

#### `T4.1-cli-interface`
- **Repo**: `source-bundler`
- **Depends on**: `T2.1-selection-and-inputs`, `T3.1-playwright-capture`, `T3.2-bundle-packager`
- **Files in scope**: `source_bundler/cli.py`, `tests/test_cli.py`
- **Constraints**: Ensure Rich status and progress output.
- **Spec**:
  1. Create Typer CLI with commands:
     - `urls [URLS...]`: accepts 1+ URLs directly.
     - `file [PATH]`: accepts plain text URL file.
     - `search-results [PATH]`: accepts JSON search results.
  2. Global/shared options:
     - `--out, -o PATH`: Output directory (defaults to `./source-bundle-YYYYMMDDTHHMMSSZ`).
     - `--interactive / --no-interactive, -i`: Interactive selection.
     - `--screenshot / --no-screenshot`: Enable/disable screenshots (default: True).
     - `--pdf / --no-pdf`: Enable/disable PDF export (default: True).
     - `--include-raw-html`: Include raw HTTP response HTML/headers (default: False).
     - `--include-links-table`: Append table of extracted links to readable markdown (default: False).
     - `--redact-pattern PATTERN`: Optional regex pattern(s) to scrub.
     - `--timeout SECONDS`: Page navigation timeout in seconds (default: 30).
     - `--concurrency INT`: Concurrent capture workers (default: 1 for deterministic serial execution).
  3. Wire execution pipeline: Parse inputs -> Interactive filter -> Capture -> Extract & AST -> Markdown & Redact -> Package bundle -> Print summary report with Rich table.
  4. Write unit tests in `tests/test_cli.py` using `typer.testing.CliRunner`.
- **Acceptance command**: `pytest tests/test_cli.py -v`

#### `T4.2-docs-and-validation`
- **Repo**: `source-bundler`
- **Depends on**: `T4.1-cli-interface`
- **Files in scope**: `README.md`
- **Constraints**: Ensure complete coverage of all prompt requirements.
- **Spec**:
  1. Write comprehensive `README.md` containing:
     - Project overview and purpose.
     - Installation instructions (`pip install -e .`, `python -m playwright install chromium`).
     - CLI command usage examples (`urls`, `file`, `search-results`, flags).
     - Output bundle structure and file descriptions (`manifest.json`, `combined.md`, `checksums.sha256`, `sources/001/...`).
     - Content extraction pipeline explanation and trade-offs.
     - Security considerations (sandboxing, untrusted content, no credentials, no shell execution).
     - Records and provenance considerations (reproducibility, fixed viewport/timezone, SHA-256 auditing).
     - Copyright, paywall, and access-control caveats.
  2. Run the complete test suite across all tests.
- **Acceptance command**: `pytest -v`

---

## Acceptance Criteria
1. Package installs cleanly in editable mode (`pip install -e .`).
2. All unit test suites pass (`pytest -v`).
3. Running `source-bundler --help` displays all subcommands (`urls`, `file`, `search-results`) and options.
4. Output directory adheres to the exact structure with `manifest.json`, `combined.md`, `checksums.sha256`, and per-source folders.
5. `manifest.json` and `checksums.sha256` use valid SHA-256 hashes and standard formats.
6. Non-fatal errors are logged in `manifest.json` and `combined.md` without aborting the batch run.
