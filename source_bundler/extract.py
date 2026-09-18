"""HTML content extraction, sanitization, and structured AST generation."""

from typing import Any, Dict, List, Optional, Tuple
import re
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from source_bundler.models import ASTBlock, ASTDocument

try:
    from readability import Document  # readability-lxml
except ImportError:
    Document = None


UNWANTED_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "nav",
    "footer",
    "header",
    "aside",
    "iframe",
    "object",
    "embed",
    "form",
    "button",
    "input",
    "select",
    "textarea",
}

COOKIE_BANNER_PATTERN = re.compile(
    r"(cookie|gdpr|consent|privacy-alert|banner-cookie|notice-cookie|cc-banner|optanon|onetrust|cmp-container)",
    re.IGNORECASE,
)


def _strip_unwanted_elements(soup: BeautifulSoup) -> None:
    """Remove scripts, styles, comments, metadata, and cookie banners from BeautifulSoup tree."""
    # Remove HTML comments
    for comment in list(soup.find_all(string=lambda text: isinstance(text, Comment))):
        comment.extract()

    # Remove unwanted tags
    for tag in list(soup.find_all(list(UNWANTED_TAGS))):
        tag.decompose()

    # Remove elements with cookie/gdpr/consent banners or alertdialog roles
    for tag in list(soup.find_all(True)):
        if not isinstance(tag, Tag) or tag.attrs is None:
            continue

        role = str(tag.get("role") or "").lower()
        aria_label = str(tag.get("aria-label") or "").lower()
        if role in ("alertdialog", "dialog") and (
            "cookie" in aria_label or "consent" in aria_label or "privacy" in aria_label
        ):
            tag.decompose()
            continue

        tag_id = str(tag.get("id") or "")
        tag_classes = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class") or "")
        combined_id_class = f"{tag_id} {tag_classes}".strip()

        if combined_id_class and COOKIE_BANNER_PATTERN.search(combined_id_class):
            tag.decompose()


def extract_readable_html(raw_html: str, url: Optional[str] = None) -> Tuple[str, str]:
    """Extract page title and main readable HTML content, stripping boilerplate and unwanted tags.
    
    Uses readability-lxml (Document) when available and falls back gracefully to BeautifulSoup
    content targeting.
    """
    if not raw_html or not raw_html.strip():
        return "", ""

    title = ""
    content_html = ""

    # Attempt extraction via readability Document
    if Document is not None:
        try:
            doc = Document(raw_html, url=url)
            readability_title = (doc.short_title() or doc.title() or "").strip()
            if readability_title and readability_title != "[no-title]":
                title = readability_title
            content_html = doc.summary(html_partial=True)
        except Exception:
            title = ""
            content_html = ""

    # Fallback to BeautifulSoup parsing if readability produced empty or failed
    if not content_html or not content_html.strip():
        soup = BeautifulSoup(raw_html, "html.parser")
        if not title:
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
            elif soup.find("h1"):
                title = soup.find("h1").get_text().strip()

        # Target main content containers
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("body")
            or soup
        )
        content_html = str(main_content)

    # Clean the content HTML
    clean_soup = BeautifulSoup(content_html, "html.parser")
    _strip_unwanted_elements(clean_soup)

    # If title is still missing, try extracting from clean soup
    if not title:
        h1 = clean_soup.find("h1")
        if h1:
            title = h1.get_text().strip()

    # Normalize returned html
    body = clean_soup.body if clean_soup.body else clean_soup
    cleaned_str = "".join(str(child) for child in body.contents).strip()
    if not cleaned_str:
        cleaned_str = str(clean_soup).strip()

    return title, cleaned_str


def _extract_text(element: Tag) -> str:
    """Extract clean whitespace-normalized text from a BeautifulSoup tag."""
    return " ".join(element.get_text().split()).strip()


def build_ast_document(source_id: str, title: str, final_url: str, cleaned_html: str) -> ASTDocument:
    """Parse cleaned HTML into a structured block-level ASTDocument representation."""
    if not cleaned_html or not cleaned_html.strip():
        return ASTDocument(source_id=source_id, title=title, final_url=final_url, blocks=[])

    soup = BeautifulSoup(cleaned_html, "html.parser")
    blocks: List[ASTBlock] = []

    # Iterate over top-level and significant semantic elements
    target_tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "blockquote", "pre", "table", "a"]

    # We collect block-level candidates from the cleaned HTML
    elements = soup.find_all(target_tags)
    
    # Track visited / nested elements to avoid duplicate sub-block extraction
    # (e.g. avoid parsing <p> or <a> inside <li> or inside <blockquote> or inside <table>)
    ignored_parents = {"ul", "ol", "li", "blockquote", "pre", "table", "thead", "tbody", "tr", "th", "td"}

    for el in elements:
        # Check if this element is nested inside another block container already being handled
        parent_tags = [p.name.lower() for p in el.parents if isinstance(p, Tag)]
        is_nested_in_container = any(pt in ignored_parents for pt in parent_tags)
        
        tag_name = el.name.lower()

        if is_nested_in_container and tag_name != "a":
            continue

        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag_name[1])
            text = _extract_text(el)
            if text:
                blocks.append(ASTBlock(type="heading", level=level, text=text))

        elif tag_name == "p":
            text = _extract_text(el)
            if text:
                blocks.append(ASTBlock(type="paragraph", text=text))

        elif tag_name in ("ul", "ol"):
            is_ordered = tag_name == "ol"
            items = []
            for li in el.find_all("li", recursive=False):
                item_text = _extract_text(li)
                if item_text:
                    items.append(item_text)
            # If no direct children found (e.g. malformed markup), find all descendant li
            if not items:
                for li in el.find_all("li"):
                    item_text = _extract_text(li)
                    if item_text:
                        items.append(item_text)
            if items:
                blocks.append(
                    ASTBlock(
                        type="list",
                        items=items,
                        extra={"ordered": is_ordered},
                    )
                )

        elif tag_name == "blockquote":
            text = _extract_text(el)
            if text:
                blocks.append(ASTBlock(type="blockquote", text=text))

        elif tag_name == "pre":
            code_el = el.find("code")
            code_text = el.get_text()
            language = None
            if code_el:
                # Check for language classes (e.g., class="language-python" or class="lang-py")
                classes = code_el.get("class", [])
                if isinstance(classes, list):
                    for cls in classes:
                        if cls.startswith("language-") or cls.startswith("lang-"):
                            language = cls.split("-", 1)[1]
                            break

            blocks.append(
                ASTBlock(
                    type="code_block",
                    text=code_text.strip("\r\n"),
                    extra={"language": language} if language else {},
                )
            )

        elif tag_name == "table":
            rows: List[List[str]] = []
            headers: List[str] = []
            
            # Look for headers
            th_cells = el.find_all("th")
            if th_cells:
                headers = [_extract_text(th) for th in th_cells]

            # Collect all tr elements
            for tr in el.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                row_data = [_extract_text(cell) for cell in cells]
                if any(row_data):
                    rows.append(row_data)

            if rows or headers:
                extra_data: Dict[str, Any] = {}
                if headers:
                    extra_data["headers"] = headers
                blocks.append(
                    ASTBlock(
                        type="table",
                        rows=rows,
                        extra=extra_data,
                    )
                )

        elif tag_name == "a":
            # Only record standalone or top-level links (not nested in p, li, etc.)
            if not any(pt in ("p", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "table", "td", "th") for pt in parent_tags):
                href = el.get("href")
                text = _extract_text(el)
                if href or text:
                    blocks.append(ASTBlock(type="link", text=text or None, href=href or None))

    return ASTDocument(
        source_id=source_id,
        title=title or None,
        final_url=final_url or None,
        blocks=blocks,
    )
