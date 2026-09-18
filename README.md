# web-source-bundler

`web-source-bundler` captures web pages for AI research. It saves clean Markdown, page screenshots, PDFs, and structured block JSON (`ast.json`), packaged into a folder with a manifest and SHA-256 checksums.

## Features

- **Multiple inputs**: Direct URLs, text files with URL lists, or search-result JSON files.
- **Interactive picking**: Pick which URLs to keep before downloading.
- **Playwright browser capture**: Headless Chromium with fixed viewport (1365x768), UTC time, and no saved cookies.
- **Clean Markdown extraction**: Strips navigation, scripts, and ads. Targets the main text.
- **Single combined file**: Outputs `combined.md` formatted for AI chat prompts.
- **Archival files**: Saves rendered HTML, full-page screenshots, and PDF printouts.
- **SHA-256 checksums**: Hashes every file for audit checks.
- **Local only**: Runs on your machine. No remote uploads, credential storage, or paywall bypass.

## Installation

Requires Python 3.10+.

1. Install `web-source-bundler`:
   ```bash
   git clone https://github.com/AndrewBrown-USDA/web-source-bundler.git
   cd web-source-bundler
   pip install -e .
   ```

2. Install the Chromium browser binary:
   ```bash
   python -m playwright install chromium
   ```

## CLI Usage

The CLI provides three subcommands: `urls`, `file`, and `search-results`. Both `web-source-bundler` and `source-bundler` work.

### 1. Direct URLs

Capture URLs passed as arguments:

```bash
web-source-bundler urls https://example.com https://www.gsa.gov --out ./bundle
```

### 2. URL List File

Capture URLs listed in a text file (one URL per line; lines starting with `#` are ignored):

```bash
web-source-bundler file urls.txt --out ./bundle
```

*Example `urls.txt`:*
```text
# Research sources
https://example.com
https://www.gsa.gov
https://docs.python.org/3/
```

### 3. Search Results JSON

Capture sources from a search result JSON file:

```bash
web-source-bundler search-results results.json --out ./bundle --interactive
```

*Example `results.json`:*
```json
[
  {
    "title": "Example Domain",
    "url": "https://example.com",
    "snippet": "Example domain for illustrative examples."
  },
  {
    "title": "General Services Administration",
    "link": "https://www.gsa.gov",
    "snippet": "Official website of the U.S. General Services Administration."
  }
]
```
*(Supports both `"url"` and `"link"` keys).*

## Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--out`, `-o` | Output directory path. | `source-bundle-<TIMESTAMP>` |
| `--interactive`, `-i` | Prompt (`[Y/n]`) for each URL. | Off |
| `--no-screenshot` | Skip PNG screenshot. | Saves screenshot |
| `--no-pdf` | Skip PDF printout. | Saves PDF |
| `--include-raw-html` | Save raw HTTP body (`raw.html`) and headers (`response_headers.json`). | Off |
| `--include-links-table` | Append a table of outbound links to `readable.md`. | Off |
| `--redact-pattern <REGEX>` | Replace matching regex with `[REDACTED]`. Can repeat. | None |
| `--timeout <SECONDS>` | Page load timeout in seconds. | `30` |
| `--version`, `-v` | Show version and exit. | — |

### Example

```bash
web-source-bundler urls https://example.com \
  --out ./my-bundle \
  --no-pdf \
  --include-links-table \
  --redact-pattern "(\d{3}-\d{2}-\d{4})" \
  --timeout 45
```

## Output Structure

The output folder contains:

```text
source-bundle-20260918T153000Z/
├── manifest.json              # Provenance metadata and error logs
├── combined.md                # Reference Markdown file for AI chat
├── checksums.sha256           # SHA-256 hashes of all files
└── sources/
    ├── 001/
    │   ├── metadata.json      # Source metadata, HTTP status, and timings
    │   ├── rendered.html      # Rendered DOM HTML
    │   ├── readable.md        # Extracted Markdown with YAML front matter
    │   ├── ast.json           # Block AST of extracted text
    │   ├── screenshot.png     # Full-page screenshot
    │   ├── page.pdf           # Vector PDF printout
    │   ├── raw.html           # Raw HTTP body (with --include-raw-html)
    │   └── response_headers.json # HTTP headers (with --include-raw-html)
    └── 002/
        └── ...
```

### Combined Markdown (`combined.md`)

`combined.md` joins all sources into one document for AI prompts:

```markdown
# Source Bundle

Bundle ID: source-bundle-20260918T153000Z
Created: 2026-09-18T15:30:00Z
Tool: web-source-bundler 0.1.0

Use this document as the reference source bundle. Cite material by source ID.

---

## Source 001: Example Domain

- Input URL: https://example.com
- Final URL: https://example.com/
- Fetched: 2026-09-18T15:30:12Z
- SHA-256 readable Markdown: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

### Content

Example Domain

This domain is for use in illustrative examples in documents.
```

## Content Extraction

1. **DOM fetch**: Playwright loads the page, waits for network idle, and reads `page.content()`.
2. **Noise removal**: Drops `<script>`, `<style>`, `<noscript>`, `<svg>`, `<canvas>`, `<nav>`, `<footer>`, `<header>`, and cookie banners.
3. **Main container search**: Looks for `<main>`, `<article>`, `[role="main"]`, `#content`, or `.content`. Falls back to `<body>`.
4. **Markdown conversion**: Uses `markdownify` to convert HTML to Markdown. Keeps headings, lists, tables, code blocks, and links.
5. **AST generation**: Traverses the cleaned DOM to build block objects in `ast.json`.
6. **Redactions & links**: Applies regex redactions and optionally appends a link table.

## Security

- **Sandboxing**: Playwright runs in a sandbox. Do not run as root or administrator.
- **Untrusted input**: Web content is treated as untrusted data and converted to static Markdown.
- **No credentials**: The tool does not store or send passwords, tokens, or cookies.
- **Local only**: No data is sent to external servers.
- **Access limits**: Does not bypass paywalls or access controls.

## Running Tests

Run tests with `pytest`:

```bash
python -m pytest -v
```
