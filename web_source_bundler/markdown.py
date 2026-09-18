"""Markdown generation and redaction utilities."""

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple, Union
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from web_source_bundler.models import Manifest


@dataclass
class ReadableSourceContext:
    """Structured context for building a readable Markdown document."""

    source_id: str
    title: str
    input_url: str
    final_url: str
    fetched_at: str
    http_status: Optional[int]
    content_md: str
    extracted_links: Optional[List[Tuple[str, str]]] = None
    include_links_table: bool = False
    redact_patterns: Optional[List[str]] = None


def html_to_markdown(html_content: str, strip_tags: Optional[List[str]] = None) -> str:
    """Convert HTML content to clean standard Markdown.
    
    Preserves headings, lists, tables, code blocks, and links.
    Optionally strips unwanted tags before conversion.
    """
    if not html_content or not html_content.strip():
        return ""

    content = html_content
    if strip_tags:
        soup = BeautifulSoup(content, "html.parser")
        for tag_name in strip_tags:
            for el in soup.find_all(tag_name):
                el.decompose()
        content = str(soup)

    markdown_text = md(
        content,
        heading_style="ATX",
        bullets="-",
        code_language="",
        autolinks=False,
    )

    # Normalize excessive newlines (max 2 consecutive newlines)
    markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text)
    return markdown_text.strip()


def apply_redactions(text: str, patterns: Optional[List[str]]) -> str:
    """Apply regex redaction patterns to text, replacing matches with [REDACTED]."""
    if not text or not patterns:
        return text

    redacted = text
    for pattern in patterns:
        if not pattern:
            continue
        try:
            regex = re.compile(pattern)
            redacted = regex.sub("[REDACTED]", redacted)
        except re.error:
            # Skip invalid regex patterns safely
            continue

    return redacted


def build_readable_markdown(
    source_id: Union[str, ReadableSourceContext] = "",
    title: str = "",
    input_url: str = "",
    final_url: str = "",
    fetched_at: str = "",
    http_status: Optional[int] = None,
    content_md: str = "",
    extracted_links: Optional[List[Tuple[str, str]]] = None,
    include_links_table: bool = False,
    redact_patterns: Optional[List[str]] = None,
    *,
    context: Optional[ReadableSourceContext] = None,
) -> str:
    """Build a standalone readable Markdown document with YAML front matter.

    Supports either a structured `ReadableSourceContext` or individual keyword parameters.
    """
    if isinstance(source_id, ReadableSourceContext):
        ctx = source_id
    elif context is not None:
        ctx = context
    else:
        ctx = ReadableSourceContext(
            source_id=source_id,
            title=title,
            input_url=input_url,
            final_url=final_url,
            fetched_at=fetched_at,
            http_status=http_status,
            content_md=content_md,
            extracted_links=extracted_links,
            include_links_table=include_links_table,
            redact_patterns=redact_patterns,
        )

    # Front matter header
    front_matter_lines = [
        "---",
        f"source_id: {ctx.source_id or ''}",
        f"title: \"{ctx.title or ''}\"",
        f"input_url: {ctx.input_url or ''}",
        f"final_url: {ctx.final_url or ''}",
        f"fetched_at: {ctx.fetched_at or ''}",
        f"http_status: {ctx.http_status if ctx.http_status is not None else ''}",
        "---",
    ]
    front_matter = "\n".join(front_matter_lines)

    # Apply redactions to content
    body = apply_redactions(ctx.content_md or "", ctx.redact_patterns).strip()

    # Optional extracted links table
    links_section = ""
    if ctx.include_links_table and ctx.extracted_links:
        table_lines = [
            "### Extracted Links",
            "",
            "| Text | URL |",
            "| --- | --- |",
        ]
        for link_text, link_url in ctx.extracted_links:
            clean_text = (link_text or "").replace("|", "\\|").replace("\n", " ").strip()
            clean_url = (link_url or "").replace("|", "\\|").strip()
            table_lines.append(f"| {clean_text} | {clean_url} |")

        links_section = "\n\n" + "\n".join(table_lines)
        links_section = apply_redactions(links_section, ctx.redact_patterns)

    parts = [front_matter]
    if body:
        parts.append(body)
    if links_section:
        parts.append(links_section.strip())

    return "\n\n".join(parts).strip() + "\n"


def build_combined_markdown(
    manifest: Manifest,
    source_markdowns: Dict[str, str],
    include_index: bool = False,
) -> str:
    """Build the single combined reference Markdown bundle containing all sources."""
    created_at_str = (
        manifest.created_at.isoformat()
        if isinstance(manifest.created_at, datetime)
        else str(manifest.created_at)
    )

    doc_lines = [
        "# Source Bundle",
        "",
        f"Bundle ID: {manifest.bundle_id}  ",
        f"Created: {created_at_str}  ",
        f"Tool: {manifest.tool.name} {manifest.tool.version}",
        "",
        "Use this document as the reference source bundle. Cite material by source ID.",
    ]

    if include_index:
        doc_lines.extend([
            "",
            "## Index",
            "| Source ID | Title | Status | SHA-256 (Markdown) |",
            "| --- | --- | --- | --- |",
        ])

        for source in manifest.sources:
            s_id = source.source_id
            s_title = (source.title or "Untitled").replace("|", "\\|")
            if source.http_status:
                status = f"HTTP {source.http_status}"
            elif source.errors:
                status = f"Error ({source.errors[-1].stage})"
            else:
                status = "Success" if source.selected else "Excluded"

            sha = source.hashes.get("readable_markdown", "-")
            doc_lines.append(f"| {s_id} | {s_title} | {status} | {sha} |")

    doc_lines.append("")

    for source in manifest.sources:
        s_id = source.source_id
        s_title = source.title or "Untitled"
        fetched_str = (
            source.fetched_at.isoformat()
            if isinstance(source.fetched_at, datetime)
            else str(source.fetched_at or "-")
        )
        sha = source.hashes.get("readable_markdown", "-")

        doc_lines.extend([
            "---",
            "",
            f"## Source {s_id}: {s_title}",
            "",
            f"- Input URL: {source.input_url}",
            f"- Final URL: {source.final_url or source.input_url}",
            f"- Fetched: {fetched_str}",
            f"- SHA-256 readable Markdown: {sha}",
            "",
            "### Content",
            "",
        ])

        content = source_markdowns.get(s_id)
        if content:
            doc_lines.append(content.strip())
        elif source.errors:
            error_msgs = "\n".join([f"- {err.stage}: {err.message}" for err in source.errors])
            doc_lines.append(f"> Capture failed for this source:\n{error_msgs}")
        else:
            doc_lines.append("*No content available.*")

        doc_lines.append("")

    return "\n".join(doc_lines).strip() + "\n"
