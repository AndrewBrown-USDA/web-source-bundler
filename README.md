# source-bundler

**`source-bundler`** is a local Python command-line utility designed to capture web sources deterministically for AI-assisted research workflows. It extracts clean, readable Markdown content from web pages, renders full-page screenshots and PDF printouts, constructs lightweight block-level ASTs, and packages everything into an upload-ready source bundle complete with audit-ready provenance metadata and cryptographic SHA-256 checksums.

---

## Key Features

- **Multi-Input Support**: Accept direct URLs as command-line arguments, plain text URL files, or search-results JSON files.
- **Interactive Source Selection**: Review URLs and snippets interactively before fetching, with include/exclude decisions recorded in metadata.
- **Deterministic Playwright Capture**: Uses headless Chromium with fixed viewport (1365x768), UTC timezone, `en-US` locale, static desktop user-agent, and disabled service workers.
- **Intelligent Content Extraction**: Cleans boilerplate, navigation, scripts, and non-content elements, targeting main semantic containers and converting content into formatted Markdown.
- **Upload-Ready Combined Markdown**: Generates a single consolidated `combined.md` file formatted with source headers and citations, perfect for direct upload into AI chat contexts.
- **Structured Block AST**: Extracts page content into a structured JSON block representation (`ast.json`) for programmatic analysis.
- **Archival Artifact Preservation**: Stores full-page screenshots (`screenshot.png`), vector PDFs (`page.pdf`), rendered DOM HTML (`rendered.html`), and optional raw HTTP response payloads and headers.
- **Tamper-Evident Integrity**: Calculates and writes SHA-256 hashes for every artifact to `checksums.sha256` and `manifest.json`.
- **Local & Secure Execution**: Operates strictly locally with no automated uploads, no credential storage, and no paywall/access-control bypass.

---

## Installation

Ensure you have Python 3.9+ installed.

1. Clone the repository and install `source-bundler` in editable mode:
   ```bash
   git clone https://github.com/example/source-bundler.git
   cd source-bundler
   pip install -e .
   ```

2. Install the required Playwright browser binary (Chromium):
   ```bash
   python -m playwright install chromium
   ```

---

## CLI Commands & Usage

`source-bundler` provides three primary subcommands to bundle web content: `urls`, `file`, and `search-results`.

### 1. Direct URLs

Capture one or more URLs directly from command-line arguments:

```bash
source-bundler urls https://example.com https://www.gsa.gov --out ./bundle
```

### 2. URL List File

Capture URLs listed in a plain text file (one URL per line; blank lines and lines starting with `#` are ignored):

```bash
source-bundler file urls.txt --out ./bundle
```

*Example `urls.txt`:*
```text
# Research sources
https://example.com
https://www.gsa.gov
https://docs.python.org/3/
```

### 3. Search Results JSON

Capture sources from a search results JSON file:

```bash
source-bundler search-results results.json --out ./bundle --interactive
```

*Example `results.json`:*
```json
[
  {
    "title": "Example Domain",
    "url": "https://example.com",
    "snippet": "Example domain for illustrative examples in documents."
  },
  {
    "title": "General Services Administration",
    "link": "https://www.gsa.gov",
    "snippet": "Official website of the U.S. General Services Administration."
  }
]
```
*(Both `"url"` and `"link"` keys are supported).*

---

## Command Options & Flags

All subcommands support common configuration flags:

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--out`, `-o` | Custom output directory path. If omitted, generates `source-bundle-<TIMESTAMP>`. | `None` (auto-generated) |
| `--interactive`, `-i` | Prompt interactively to confirm (`[Y/n]`) inclusion of each candidate URL. | `False` |
| `--no-screenshot` | Disable capturing full-page screenshot PNGs. | Screenshots enabled |
| `--no-pdf` | Disable exporting pages as PDF documents. | PDF export enabled |
| `--include-raw-html` | Capture raw HTTP response body (`raw.html`) and HTTP response headers (`response_headers.json`). | `False` |
| `--include-links-table` | Append a Markdown table of all extracted outbound hyperlinks to `readable.md`. | `False` |
| `--redact-pattern <REGEX>` | Redact matching regex patterns (e.g. emails, tokens) from extracted Markdown (`[REDACTED]`). Can be passed multiple times. | `None` |
| `--timeout <SECONDS>` | Page navigation and rendering timeout in seconds. | `30` |
| `--version`, `-v` | Display tool version and exit. | — |

### Example with Advanced Flags

```bash
source-bundler urls https://example.com \
  --out ./my-research-bundle \
  --no-pdf \
  --include-links-table \
  --redact-pattern "(\d{3}-\d{2}-\d{4})" \
  --timeout 45
```

---

## Output Directory & Artifact Structure

When execution completes, `source-bundler` creates a self-contained bundle directory containing consolidated research files, checksums, and per-source archival artifacts:

```text
source-bundle-20260918T153000Z/
├── manifest.json              # Complete machine-readable provenance & audit log
├── combined.md                # Consolidated upload-ready reference Markdown for AI chat
├── checksums.sha256           # Cryptographic SHA-256 hashes of all artifacts
└── sources/
    ├── 001/
    │   ├── metadata.json      # Per-source capture metadata, HTTP status, and timings
    │   ├── rendered.html      # Fully rendered DOM HTML after JavaScript execution
    │   ├── readable.md        # Extracted main content in Markdown with YAML front matter
    │   ├── ast.json           # Structured block-level AST of extracted content
    │   ├── screenshot.png     # Full-page screenshot (if enabled)
    │   ├── page.pdf           # Vector PDF printout (if enabled)
    │   ├── raw.html           # Raw HTTP response body (if --include-raw-html)
    │   └── response_headers.json # HTTP response headers (if --include-raw-html)
    └── 002/
        └── ...
```

### Combined Markdown Format (`combined.md`)

The `combined.md` file is tailored specifically for LLM context windows, providing a clean citation structure:

```markdown
# Source Bundle

Bundle ID: source-bundle-20260918T153000Z
Created: 2026-09-18T15:30:00Z
Tool: source-bundler 0.1.0

Use this document as the reference source bundle. Cite material by source ID.

---

## Source 001: Example Domain

- Input URL: https://example.com
- Final URL: https://example.com/
- Fetched: 2026-09-18T15:30:12Z
- SHA-256 readable Markdown: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

### Content

Example Domain

This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.
```

---

## Content Extraction Pipeline & Tradeoffs

`source-bundler` implements a pragmatic, robust content extraction pipeline designed to maximize text fidelity while stripping distracting web clutter:

1. **DOM Capture**: Playwright loads the page, waits for `domcontentloaded` and network idle stabilization, and retrieves the live DOM HTML (`page.content()`).
2. **Boilerplate & Noise Removal**: Non-content elements are removed (`<script>`, `<style>`, `<noscript>`, `<svg>`, `<canvas>`, `<nav>`, `<footer>`, `<header>`, cookie banners, and dialog elements).
3. **Semantic Container Targeting**: Content extraction prioritizes semantic main content nodes (`<main>`, `<article>`, `[role="main"]`, `#content`, `.content`, `.main`). If none are found, extraction falls back safely to `<body>`.
4. **Markdown Conversion**: Uses `markdownify` with fine-tuned heading styles (`ATX`), robust table preservation, fenced code blocks, and link preservation.
5. **Structured AST Generation**: Traverses the cleaned DOM hierarchy to build a block-level AST (`heading`, `paragraph`, `code_block`, `blockquote`, `list`, `table`, `link`) saved to `ast.json`.
6. **Redaction & Link Indexing**: Optional regex redactions are applied across Markdown content, and an optional outbound links reference table can be appended.

### Tradeoffs
- **Heuristic Content Isolation vs. Readability Engines**: Rather than relying strictly on heavy algorithmic readability models that may discard custom data tables or technical documentation sidebars, `source-bundler` combines semantic container heuristics with DOM hygiene to preserve complex structures like code blocks and tables.
- **Client-Side Rendering**: Headless Chromium execution ensures modern single-page applications (SPAs) render completely, at the cost of higher CPU/memory overhead compared to static HTTP requests.

---

## Provenance & Records Review

`source-bundler` is designed to meet strict provenance and auditability standards for research reproducibility:

- **Deterministic Browser Environment**:
  - Viewport: Fixed at `1365x768`
  - Locale: `en-US`
  - Timezone: `UTC`
  - User-Agent: Static desktop user agent
  - Isolation: Transient browser contexts with service workers disabled and no cookie persistence across runs.
- **Cryptographic Verification**: Every output file is hashed using SHA-256. Hashes are recorded in `checksums.sha256` and mapped to corresponding source records in `manifest.json`.
- **Comprehensive Manifest**: `manifest.json` provides an end-to-end record of the execution, including the capture configuration, tool version, ISO-8601 UTC timestamps, HTTP status codes, final resolved URLs (tracking redirects), user selection notes, artifact paths, and non-fatal error traces.

---

## Security & Access Control Considerations

- **Browser Sandboxing**: Playwright operates in standard sandboxed browser processes. Do not disable sandboxing or execute the CLI with root/administrator privileges.
- **Untrusted Content Handling**: All fetched web assets are treated as untrusted data. DOM HTML is sanitized and converted to static Markdown before being passed to downstream AI workflows.
- **No Credential Access**: The tool does not store, request, or transmit credentials, session tokens, or authentication cookies.
- **No Automatic Remote Transmissions**: The tool is strictly a local capture and packaging utility. It does not perform automated uploads to any external AI service or third-party server.
- **Ethical Web Ingestion**: `source-bundler` does not attempt to circumvent CAPTCHAs, paywalls, or access controls.

---

## Running Tests

Run the comprehensive unit test suite using `pytest`:

```bash
python -m pytest -v
```
