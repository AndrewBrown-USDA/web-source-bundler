"""Unit tests for web_source_bundler.markdown."""

from datetime import datetime, timezone
import pytest

from web_source_bundler.markdown import (
    apply_redactions,
    build_combined_markdown,
    build_readable_markdown,
    html_to_markdown,
)
from web_source_bundler.models import (
    ArtifactRefs,
    CaptureConfig,
    Manifest,
    SourceError,
    SourceRecord,
    ToolInfo,
)


def test_html_to_markdown_basic():
    html = """
    <h1>Main Title</h1>
    <p>This is a paragraph with <a href="https://example.com">a link</a> and <strong>bold</strong> text.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    """
    md = html_to_markdown(html)
    assert "# Main Title" in md
    assert "[a link](https://example.com)" in md
    assert "**bold**" in md
    assert "- Item 1" in md
    assert "- Item 2" in md


def test_html_to_markdown_strip_tags():
    html = """
    <nav><a href="/home">Home</a></nav>
    <article>
        <h2>Article Heading</h2>
        <p>Article body.</p>
    </article>
    <script>alert('malicious');</script>
    <footer>Footer notes</footer>
    """
    md = html_to_markdown(html, strip_tags=["nav", "script", "footer"])
    assert "Home" not in md
    assert "alert" not in md
    assert "Footer notes" not in md
    assert "## Article Heading" in md
    assert "Article body." in md


def test_html_to_markdown_empty_or_whitespace():
    assert html_to_markdown("") == ""
    assert html_to_markdown("   \n\t ") == ""


def test_html_to_markdown_code_and_table():
    html = """
    <pre><code>def hello():\n    return "world"</code></pre>
    <table>
        <thead>
            <tr><th>Header 1</th><th>Header 2</th></tr>
        </thead>
        <tbody>
            <tr><td>Val 1</td><td>Val 2</td></tr>
        </tbody>
    </table>
    """
    md = html_to_markdown(html)
    assert "def hello():" in md
    assert "Header 1" in md
    assert "Val 1" in md


def test_apply_redactions_single_and_multiple_patterns():
    text = "User email is test@example.com and API_KEY=sk-1234567890abcdef."
    patterns = [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", r"sk-[a-f0-9]+"]
    redacted = apply_redactions(text, patterns)
    assert "test@example.com" not in redacted
    assert "sk-1234567890abcdef" not in redacted
    assert "User email is [REDACTED] and API_KEY=[REDACTED]." == redacted


def test_apply_redactions_none_and_empty():
    text = "Clean text without redactions."
    assert apply_redactions(text, None) == text
    assert apply_redactions(text, []) == text
    assert apply_redactions(text, [""]) == text
    assert apply_redactions("", [r"\d+"]) == ""


def test_apply_redactions_invalid_regex():
    text = "Text with (broken regex"
    # An invalid regex like unclosed parenthesis shouldn't raise exception
    res = apply_redactions(text, [r"(unclosed"])
    assert res == text


def test_build_readable_markdown_front_matter_and_content():
    md = build_readable_markdown(
        source_id="001",
        title="Test Title",
        input_url="https://example.com",
        final_url="https://example.com/final",
        fetched_at="2026-09-18T12:00:00Z",
        http_status=200,
        content_md="# Content\n\nSome secret info: token-secret-999",
        redact_patterns=[r"token-secret-\d+"],
    )

    assert md.startswith("---\n")
    assert "source_id: 001" in md
    assert 'title: "Test Title"' in md
    assert "input_url: https://example.com" in md
    assert "final_url: https://example.com/final" in md
    assert "fetched_at: 2026-09-18T12:00:00Z" in md
    assert "http_status: 200" in md
    assert "---" in md
    assert "token-secret-999" not in md
    assert "Some secret info: [REDACTED]" in md


def test_build_readable_markdown_with_links_table():
    links = [("Home", "https://example.com/home"), ("Secret Link", "https://example.com/token-123")]
    md = build_readable_markdown(
        source_id="002",
        title="Links Test",
        input_url="https://example.com",
        final_url="https://example.com",
        fetched_at="2026-09-18T12:00:00Z",
        http_status=200,
        content_md="Body content",
        extracted_links=links,
        include_links_table=True,
        redact_patterns=[r"token-\d+"],
    )

    assert "### Extracted Links" in md
    assert "| Text | URL |" in md
    assert "| Home | https://example.com/home |" in md
    assert "token-123" not in md
    assert "[REDACTED]" in md


def test_build_combined_markdown_complete():
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    manifest = Manifest(
        bundle_id="source-bundle-20260918T120000Z",
        created_at=now,
        tool=ToolInfo(name="web-source-bundler", version="0.1.0"),
        capture_config=CaptureConfig(),
        sources=[
            SourceRecord(
                source_id="001",
                input_url="https://example.com/1",
                final_url="https://example.com/1",
                title="First Source",
                fetched_at=now,
                http_status=200,
                hashes={"readable_markdown": "abc123sha"},
                artifacts=ArtifactRefs(readable_markdown="sources/001-first-source.md"),
            ),
            SourceRecord(
                source_id="002",
                input_url="https://example.com/2",
                title="Failed Source",
                fetched_at=now,
                errors=[SourceError(stage="fetch", message="404 Not Found", timestamp=now)],
            ),
        ],
    )

    source_markdowns = {
        "001": "# First Source\n\nThis is the markdown body of source 1.",
    }

    combined = build_combined_markdown(manifest, source_markdowns, include_index=True)

    assert "# Source Bundle" in combined
    assert "Bundle ID: source-bundle-20260918T120000Z" in combined
    assert "Tool: web-source-bundler 0.1.0" in combined
    assert "Cite material by source ID." in combined
    assert "## Index" in combined
    assert "| 001 | First Source | HTTP 200 | abc123sha |" in combined
    assert "| 002 | Failed Source | Error (fetch) | - |" in combined

    assert "## Source 001: First Source" in combined
    assert "- Input URL: https://example.com/1" in combined
    assert "- SHA-256 readable Markdown: abc123sha" in combined
    assert "This is the markdown body of source 1." in combined

    assert "## Source 002: Failed Source" in combined
    assert "Capture failed for this source:" in combined
    assert "- fetch: 404 Not Found" in combined
