You are a senior Python engineer. Implement a local command-line tool that captures web sources for AI-assisted research workflows. The tool should accept either direct URLs or a search-results JSON file, allow optional user selection of URLs, render selected pages with Playwright, extract readable content, convert it to Markdown, and generate an upload-ready source bundle with provenance metadata suitable for records/audit review.

The goal is to produce deterministic, reproducible source packages that can be uploaded into an AI chat system as reference material, while separately preserving richer archival artifacts.

### Project name

`source-bundler`

### Primary goals

Build a Python CLI that can:

1. Accept a list of URLs from the command line or an input file.
2. Optionally accept search results in JSON format.
3. Let the user select/deselect URLs interactively.
4. Fetch and render each selected URL using Playwright.
5. Save raw HTTP response metadata where available.
6. Save rendered DOM HTML.
7. Save a screenshot.
8. Save a PDF printout where possible.
9. Extract main readable content.
10. Convert extracted content to Markdown.
11. Generate a Markdown AST or structured JSON representation.
12. Generate a consolidated `combined.md` file suitable for upload to an AI chat.
13. Generate a `manifest.json` file with provenance metadata.
14. Generate SHA-256 checksums for all important artifacts.
15. Package everything into an output directory.

### Important constraints

- Implement in Python.
- Use Playwright for browser rendering.
- Prefer deterministic behavior:
  - fixed viewport,
  - fixed user agent,
  - fixed timezone if possible,
  - fixed locale,
  - configurable timeout,
  - no persistent browser profile by default,
  - disable service workers if possible,
  - do not reuse cookies unless explicitly requested.
- Do not execute shell commands on page content.
- Sanitize filenames derived from URLs.
- Do not upload anything automatically. This is a local capture and packaging tool only.
- Do not bypass paywalls, authentication, robots restrictions, or access controls.
- Clearly mark failures in the manifest instead of silently skipping them.

### Suggested package structure

Create the following Python package:

```text
source_bundler/
  __init__.py
  cli.py
  models.py
  capture.py
  extract.py
  markdown.py
  bundle.py
  hashing.py
  selection.py
  utils.py
tests/
  test_utils.py
  test_hashing.py
  test_markdown.py
pyproject.toml
README.md
```

### CLI interface

Use `typer` or `argparse`. Prefer `typer` if reasonable.

The CLI should support:

```bash
source-bundler urls https://example.com https://www.gsa.gov --out ./bundle
```

```bash
source-bundler file urls.txt --out ./bundle
```

```bash
source-bundler search-results results.json --out ./bundle --interactive
```

```bash
source-bundler urls https://example.com --out ./bundle --no-pdf --no-screenshot
```

```bash
source-bundler urls https://example.com --out ./bundle --include-raw-html
```

### Input formats

#### Plain URL file

One URL per line. Ignore blank lines and lines beginning with `#`.

Example:

```text
https://example.com
https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro
```

#### Search results JSON

Support a generic format like:

```json
[
  {
    "title": "Example result",
    "url": "https://example.com",
    "snippet": "Example snippet..."
  }
]
```

Also support `link` as an alias for `url`.

### Interactive selection

If `--interactive` is used, show the user each candidate:

```text
[1] Example result
    https://example.com
    Example snippet...

Include this source? [Y/n]:
```

Default should be yes.

Record the user’s include/exclude decision in `manifest.json`.

### Output directory format

Generate this structure:

```text
source-bundle-YYYYMMDDTHHMMSSZ/
  manifest.json
  combined.md
  checksums.sha256
  sources/
    001/
      metadata.json
      rendered.html
      readable.md
      ast.json
      screenshot.png
      page.pdf
    002/
      metadata.json
      rendered.html
      readable.md
      ast.json
      screenshot.png
      page.pdf
```

If raw HTTP capture is implemented, include:

```text
      response_headers.json
      raw.html
```

If an artifact is disabled or unavailable, omit it but record that in metadata.

### Manifest schema

`manifest.json` should include:

```json
{
  "bundle_id": "source-bundle-20260918T153000Z",
  "created_at": "2026-09-18T15:30:00Z",
  "tool": {
    "name": "source-bundler",
    "version": "0.1.0"
  },
  "capture_config": {
    "viewport": {
      "width": 1365,
      "height": 768
    },
    "locale": "en-US",
    "timezone": "UTC",
    "user_agent": "..."
  },
  "sources": [
    {
      "source_id": "001",
      "input_url": "https://example.com",
      "final_url": "https://example.com/",
      "title": "Example Domain",
      "selected": true,
      "selection_note": null,
      "fetched_at": "2026-09-18T15:30:12Z",
      "http_status": 200,
      "content_type": "text/html",
      "artifacts": {
        "rendered_html": "sources/001/rendered.html",
        "readable_markdown": "sources/001/readable.md",
        "ast_json": "sources/001/ast.json",
        "screenshot": "sources/001/screenshot.png",
        "pdf": "sources/001/page.pdf"
      },
      "hashes": {
        "rendered_html": "sha256:...",
        "readable_markdown": "sha256:...",
        "ast_json": "sha256:..."
      },
      "errors": []
    }
  ]
}
```

If capture fails:

```json
{
  "source_id": "002",
  "input_url": "https://bad.example",
  "selected": true,
  "errors": [
    {
      "stage": "capture",
      "message": "Timeout after 30000ms"
    }
  ]
}
```

### Content extraction requirements

Implement a reasonable extraction pipeline:

1. Use Playwright to render the page.
2. Get `document.title`.
3. Get final URL.
4. Get rendered HTML from `page.content()`.
5. Remove obviously unwanted elements:
   - `script`
   - `style`
   - `noscript`
   - `svg`
   - `canvas`
   - navigation landmarks if easy:
     - `nav`
     - `footer`
     - cookie banners where detectable
6. Prefer extracting from:
   - `main`
   - `article`
   - `[role="main"]`
   - otherwise `body`
7. Preserve:
   - headings,
   - paragraphs,
   - ordered and unordered lists,
   - blockquotes,
   - tables if feasible,
   - code blocks,
   - links with hrefs.
8. Convert to Markdown.

Use libraries where helpful:

- `beautifulsoup4`
- `markdownify`
- `html2text`
- `readability-lxml`
- `lxml`

Choose a pragmatic approach. Document tradeoffs in the README.

### Markdown requirements

Each `readable.md` should start with YAML front matter:

```yaml
---
source_id: "001"
title: "Example Domain"
input_url: "https://example.com"
final_url: "https://example.com/"
fetched_at: "2026-09-18T15:30:12Z"
http_status: 200
---
```

Then include extracted Markdown content.

The combined file should look like:

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
- SHA-256 readable Markdown: sha256:...

### Content

Example Domain

This domain is for use in illustrative examples...
```

### AST requirements

Generate `ast.json` representing the extracted content in a simple block structure. It does not need to be a full Markdown AST. Example:

```json
{
  "source_id": "001",
  "title": "Example Domain",
  "blocks": [
    {
      "type": "heading",
      "level": 1,
      "text": "Example Domain"
    },
    {
      "type": "paragraph",
      "text": "This domain is for use in illustrative examples..."
    },
    {
      "type": "link",
      "text": "More information",
      "href": "https://www.iana.org/domains/example"
    }
  ]
}
```

### Playwright capture details

Use async Playwright if convenient.

Default browser behavior:

- Chromium.
- Headless mode.
- Viewport: 1365x768.
- Locale: `en-US`.
- Timezone: `UTC`.
- User agent: define a stable desktop user agent string.
- Navigation wait condition: try `domcontentloaded`, then wait briefly for network idle or fixed delay.
- Timeout: configurable, default 30 seconds.
- Do not persist cookies.
- Disable downloads.
- Do not use credentials.

Capture:

- `page.goto(url, wait_until="domcontentloaded")`
- wait for `networkidle` if possible, but avoid indefinite wait
- screenshot full page
- PDF print using Playwright Chromium if enabled
- `page.content()`
- page title
- final URL
- status from response object if available
- headers from response object if available

### Hashing

Implement SHA-256 hashing for:

- rendered HTML,
- readable Markdown,
- AST JSON,
- screenshot,
- PDF,
- manifest,
- combined.md.

Generate `checksums.sha256` in standard format:

```text
<hexhash>  manifest.json
<hexhash>  combined.md
<hexhash>  sources/001/readable.md
```

Also include selected artifact hashes in metadata and manifest.

### Error handling

The tool should continue when one URL fails.

For each source:

- record errors in `metadata.json`,
- include errors in `manifest.json`,
- include a short failure notice in `combined.md`.

Do not crash the whole run unless initialization fails.

### README requirements

Document:

- what the tool does,
- installation,
- Playwright browser installation,
- examples,
- output structure,
- limitations,
- records/provenance considerations,
- security considerations,
- copyright/access-control caveats.

Include installation commands:

```bash
pip install -e .
python -m playwright install chromium
```

### Testing

Add basic unit tests for:

- URL file parsing,
- filename sanitization,
- SHA-256 hashing,
- combined Markdown generation,
- AST generation from small sample HTML.

Do not require live internet access for unit tests.

### Dependencies

Use reasonable modern Python dependencies. Suggested:

```toml
typer
playwright
beautifulsoup4
markdownify
pydantic
python-slugify
rich
```

If you choose alternatives, document why.

### Acceptance criteria

The implementation is complete when:

1. I can install it locally with `pip install -e .`.
2. I can run `python -m playwright install chromium`.
3. I can run:

```bash
source-bundler urls https://example.com --out ./test-bundle
```

4. The output directory contains:
   - `manifest.json`,
   - `combined.md`,
   - `checksums.sha256`,
   - `sources/001/metadata.json`,
   - `sources/001/rendered.html`,
   - `sources/001/readable.md`,
   - `sources/001/ast.json`,
   - screenshot and PDF unless disabled.
5. `combined.md` is readable and suitable for upload into an AI chat.
6. `manifest.json` records provenance and errors.
7. The tool continues when individual URLs fail.
8. Unit tests pass.

### Nice-to-have features

If time permits, add:

- `--format warc` or WARC export support.
- `--save-raw` for raw HTTP response body.
- `--javascript off` mode using plain HTTP fetch.
- `--max-pages`.
- `--same-domain-only` crawling.
- `--depth 1` limited crawling.
- Deduplication by final URL.
- Deduplication by content hash.
- Robots.txt awareness.
- `--redact-pattern` option for local redaction before generating upload-ready Markdown.
- `--include-links-table` that appends all extracted links.
- `--query` option that uses a configurable search API.
- A simple local HTML report for reviewing captured sources.

### Security note

This tool will open arbitrary URLs in a browser automation environment. Treat arbitrary websites as untrusted. Keep the browser sandbox enabled. Do not run as an administrator. Do not provide credentials. Do not use a persistent browser profile by default. Do not auto-submit forms or click unknown elements.

