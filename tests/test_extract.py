"""Unit tests for HTML extraction, sanitization, and AST generation."""

import pytest
from web_source_bundler.extract import extract_readable_html, build_ast_document
from web_source_bundler.models import ASTDocument, ASTBlock


def test_extract_readable_html_basic():
    raw_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sample Article Title</title>
        <style>body { font-size: 14px; }</style>
        <script>console.log("tracking script");</script>
    </head>
    <body>
        <nav><a href="/home">Home</a><a href="/about">About</a></nav>
        <main>
            <h1>Main Heading</h1>
            <p>This is the first paragraph of meaningful content.</p>
            <p>Here is another paragraph with some <strong>bold</strong> text.</p>
        </main>
        <footer>
            <p>Copyright 2026 Test Corp</p>
        </footer>
    </body>
    </html>
    """
    title, cleaned_html = extract_readable_html(raw_html, url="https://example.com/article")
    assert "Sample Article Title" in title or "Main Heading" in title
    assert "tracking script" not in cleaned_html
    assert "<script" not in cleaned_html
    assert "<style" not in cleaned_html
    assert "<nav" not in cleaned_html
    assert "<footer" not in cleaned_html
    assert "This is the first paragraph" in cleaned_html


def test_extract_readable_html_cookie_removal():
    raw_html = """
    <html>
    <head><title>GDPR Test</title></head>
    <body>
        <div id="cookie-banner" class="cookie-notice">
            <p>We use cookies to track everything.</p>
            <button>Accept All</button>
        </div>
        <div role="dialog" aria-label="Privacy Consent">
            <p>Please accept our privacy policy.</p>
        </div>
        <article>
            <h1>Article Title</h1>
            <p>Real content goes here.</p>
        </article>
    </body>
    </html>
    """
    title, cleaned_html = extract_readable_html(raw_html)
    assert "cookie" not in cleaned_html.lower() or "Real content" in cleaned_html
    assert "We use cookies" not in cleaned_html
    assert "Please accept our privacy policy" not in cleaned_html
    assert "Real content goes here." in cleaned_html


def test_extract_readable_html_fallback():
    raw_html = "<div><h1>Direct Title</h1><p>Minimal snippet body.</p></div>"
    title, cleaned_html = extract_readable_html(raw_html)
    assert title == "Direct Title"
    assert "Minimal snippet body." in cleaned_html


def test_extract_readable_html_empty():
    title, cleaned = extract_readable_html("")
    assert title == ""
    assert cleaned == ""

    title, cleaned = extract_readable_html("   ")
    assert title == ""
    assert cleaned == ""


def test_build_ast_document_headings_and_paragraphs():
    html_content = """
    <h1>Main Title</h1>
    <p>Introductory paragraph.</p>
    <h2>Subheading Level 2</h2>
    <p>Details paragraph under subheading.</p>
    <h3>Deep Heading 3</h3>
    <p>Paragraph inside deep section.</p>
    """
    doc = build_ast_document(
        source_id="001",
        title="Main Title",
        final_url="https://example.com/doc",
        cleaned_html=html_content,
    )
    assert isinstance(doc, ASTDocument)
    assert doc.source_id == "001"
    assert doc.title == "Main Title"
    assert doc.final_url == "https://example.com/doc"

    blocks = doc.blocks
    assert len(blocks) == 6

    assert blocks[0].type == "heading"
    assert blocks[0].level == 1
    assert blocks[0].text == "Main Title"

    assert blocks[1].type == "paragraph"
    assert blocks[1].text == "Introductory paragraph."

    assert blocks[2].type == "heading"
    assert blocks[2].level == 2
    assert blocks[2].text == "Subheading Level 2"

    assert blocks[3].type == "paragraph"
    assert blocks[3].text == "Details paragraph under subheading."

    assert blocks[4].type == "heading"
    assert blocks[4].level == 3
    assert blocks[4].text == "Deep Heading 3"

    assert blocks[5].type == "paragraph"
    assert blocks[5].text == "Paragraph inside deep section."


def test_build_ast_document_lists():
    html_content = """
    <p>Items list:</p>
    <ul>
        <li>First item</li>
        <li>Second item with <em>emphasis</em></li>
        <li>Third item</li>
    </ul>
    <ol>
        <li>Step one</li>
        <li>Step two</li>
    </ol>
    """
    doc = build_ast_document("002", "Lists", "https://example.com/lists", html_content)
    assert len(doc.blocks) == 3

    assert doc.blocks[0].type == "paragraph"
    assert doc.blocks[0].text == "Items list:"

    assert doc.blocks[1].type == "list"
    assert doc.blocks[1].items == ["First item", "Second item with emphasis", "Third item"]
    assert doc.blocks[1].extra.get("ordered") is False

    assert doc.blocks[2].type == "list"
    assert doc.blocks[2].items == ["Step one", "Step two"]
    assert doc.blocks[2].extra.get("ordered") is True


def test_build_ast_document_code_blocks():
    html_content = """
    <p>Sample code:</p>
    <pre><code class="language-python">def hello():
    print("world")
</code></pre>
    <pre><code>plain code snippet</code></pre>
    """
    doc = build_ast_document("003", "Code", "https://example.com/code", html_content)
    assert len(doc.blocks) == 3

    assert doc.blocks[1].type == "code_block"
    assert doc.blocks[1].text == 'def hello():\n    print("world")'
    assert doc.blocks[1].extra.get("language") == "python"

    assert doc.blocks[2].type == "code_block"
    assert doc.blocks[2].text == "plain code snippet"
    assert "language" not in doc.blocks[2].extra or doc.blocks[2].extra.get("language") is None


def test_build_ast_document_tables():
    html_content = """
    <table>
        <thead>
            <tr><th>Header 1</th><th>Header 2</th></tr>
        </thead>
        <tbody>
            <tr><td>Cell 1A</td><td>Cell 1B</td></tr>
            <tr><td>Cell 2A</td><td>Cell 2B</td></tr>
        </tbody>
    </table>
    """
    doc = build_ast_document("004", "Table Doc", "https://example.com/table", html_content)
    assert len(doc.blocks) == 1

    tbl = doc.blocks[0]
    assert tbl.type == "table"
    assert tbl.extra.get("headers") == ["Header 1", "Header 2"]
    assert tbl.rows == [["Header 1", "Header 2"], ["Cell 1A", "Cell 1B"], ["Cell 2A", "Cell 2B"]]


def test_build_ast_document_blockquotes_and_links():
    html_content = """
    <blockquote>
        <p>This is an important quote from a famous author.</p>
    </blockquote>
    <a href="https://example.com/external">Visit Example</a>
    """
    doc = build_ast_document("005", "Quote and Link", "https://example.com", html_content)
    assert len(doc.blocks) == 2

    assert doc.blocks[0].type == "blockquote"
    assert doc.blocks[0].text == "This is an important quote from a famous author."

    assert doc.blocks[1].type == "link"
    assert doc.blocks[1].text == "Visit Example"
    assert doc.blocks[1].href == "https://example.com/external"


def test_build_ast_document_empty_or_whitespace():
    doc = build_ast_document("006", "Empty", "https://example.com", "")
    assert len(doc.blocks) == 0

    doc2 = build_ast_document("007", "Whitespace", "https://example.com", "   \n\t  ")
    assert len(doc2.blocks) == 0
