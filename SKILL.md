---
name: web-source-bundler
author: Andrew G. Brown (https://github.com/brownag)
license: MIT
version: 1.0.0
description: Captures web sources and compiles deterministic Markdown reference bundles with metadata and checksums. Use when asked to capture URLs, research web links, bundle search results, or archive web pages into an LLM-ready reference document.
---

# Web Source Bundler

Capture URLs, file lists, or search results into deterministic AI-ready reference bundles with SHA-256 provenance using `web-source-bundler`.

## Instructions

1. **Extract source inputs** from user prompt:
   - Specific URLs: `https://...`
   - File references containing URLs (`.txt` or `.json` search results)
   - Search result lists (JSON objects with `url`/`link`, `title`, `snippet`)
2. **Determine execution options** based on user constraints:
   - Output destination: `--out <dir>` (defaults to `./source-bundle-<timestamp>`)
   - Interactive prompt: `--interactive` if user requested manual selection
   - Artifacts: `--no-screenshot`, `--no-pdf`, `--include-raw-html`
   - Data privacy: `--redact-pattern "<regex>"` if sensitive tokens/PII are mentioned
   - Link indexing: `--include-links-table` if an appendix of all extracted links is requested
3. **Run `web-source-bundler` command**:
   - For direct URLs:
     ```bash
     web-source-bundler urls https://example.com https://another.com --out ./bundle
     ```
   - For URL lists:
     ```bash
     web-source-bundler file urls.txt --out ./bundle
     ```
   - For search results JSON:
     ```bash
     web-source-bundler search-results results.json --out ./bundle
     ```
4. **Inspect output bundle**:
   - Read `manifest.json` to verify capture status and review any reported errors.
   - Reference `combined.md` for conversational grounding and reference citation by Source ID (e.g., `Source 001`).
5. **Report summary** to the user:
   - State the bundle ID, output path, count of captured sources, and cite the primary contents from `combined.md`.

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Fix |
|---|---|---|
| Ad-hoc curl/wget scraping | Misses dynamic JS rendering, screenshots, and PDFs | Run `web-source-bundler` with headless Playwright |
| Silent error swallowing | Corrupts audit records and provenance | Check `manifest.json` and report any failed URLs |
| Omitting source citations | Loses verifiable provenance | Reference findings by `Source ID` from `combined.md` |
