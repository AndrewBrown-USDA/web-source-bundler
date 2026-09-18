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


def _extract_page_title(soup: BeautifulSoup) -> str:
    """Extract page title from BeautifulSoup tree checking title tag and h1 tag."""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        clean = title_tag.string.strip()
        if clean:
            return clean
    h1 = soup.find("h1")
    if h1:
        clean = h1.get_text().strip()
        if clean:
            return clean
    return ""


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
            title = _extract_page_title(soup)

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
        title = _extract_page_title(clean_soup)

    # Normalize returned html
    body = clean_soup.body if clean_soup.body else clean_soup
    cleaned_str = "".join(str(child) for child in body.contents).strip()
    if not cleaned_str:
        cleaned_str = str(clean_soup).strip()

    return title, cleaned_str


def _extract_text(element: Tag) -> str:
    """Extract clean whitespace-normalized text from a BeautifulSoup tag."""
    return " ".join(element.get_text().split()).strip()


def _ast_heading(el: Tag, tag_name: str) -> Optional[ASTBlock]:
    """Convert heading tag to ASTBlock."""
    level = int(tag_name[1])
    text = _extract_text(el)
    if text:
        return ASTBlock(type="heading", level=level, text=text)
    return None


def _ast_paragraph(el: Tag) -> Optional[ASTBlock]:
    """Convert paragraph tag to ASTBlock."""
    text = _extract_text(el)
    if text:
        return ASTBlock(type="paragraph", text=text)
    return None


def _ast_list(el: Tag, tag_name: str) -> Optional[ASTBlock]:
    """Convert ul or ol list tag to ASTBlock."""
    is_ordered = tag_name == "ol"
    items: List[str] = []
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
        return ASTBlock(
            type="list",
            items=items,
            extra={"ordered": is_ordered},
        )
    return None


def _ast_blockquote(el: Tag) -> Optional[ASTBlock]:
    """Convert blockquote tag to ASTBlock."""
    text = _extract_text(el)
    if text:
        return ASTBlock(type="blockquote", text=text)
    return None


def _ast_code_block(el: Tag) -> Optional[ASTBlock]:
    """Convert pre tag to code_block ASTBlock."""
    code_el = el.find("code")
    code_text = el.get_text()
    language = None
    if code_el:
        classes = code_el.get("class", [])
        if isinstance(classes, list):
            for cls in classes:
                if cls.startswith("language-") or cls.startswith("lang-"):
                    language = cls.split("-", 1)[1]
                    break

    return ASTBlock(
        type="code_block",
        text=code_text.strip("\r\n"),
        extra={"language": language} if language else {},
    )


def _ast_table(el: Tag) -> Optional[ASTBlock]:
    """Convert table tag to ASTBlock."""
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
        return ASTBlock(
            type="table",
            rows=rows,
            extra=extra_data,
        )
    return None


def _ast_link(el: Tag, parent_tags: List[str]) -> Optional[ASTBlock]:
    """Convert standalone link tag to ASTBlock."""
    ignored_parents = {"p", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "table", "td", "th"}
    if not any(pt in ignored_parents for pt in parent_tags):
        href = el.get("href")
        text = _extract_text(el)
        if href or text:
            return ASTBlock(type="link", text=text or None, href=href or None)
    return None


def _ast_for_tag(el: Tag, parent_tags: List[str]) -> Optional[ASTBlock]:
    """Convert a BeautifulSoup tag element into an ASTBlock if applicable."""
    tag_name = el.name.lower()
    ignored_parents = {"ul", "ol", "li", "blockquote", "pre", "table", "thead", "tbody", "tr", "th", "td"}
    is_nested_in_container = any(pt in ignored_parents for pt in parent_tags)

    if is_nested_in_container and tag_name != "a":
        return None

    if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return _ast_heading(el, tag_name)
    elif tag_name == "p":
        return _ast_paragraph(el)
    elif tag_name in ("ul", "ol"):
        return _ast_list(el, tag_name)
    elif tag_name == "blockquote":
        return _ast_blockquote(el)
    elif tag_name == "pre":
        return _ast_code_block(el)
    elif tag_name == "table":
        return _ast_table(el)
    elif tag_name == "a":
        return _ast_link(el, parent_tags)

    return None


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

    for el in elements:
        parent_tags = [p.name.lower() for p in el.parents if isinstance(p, Tag)]
        block = _ast_for_tag(el, parent_tags)
        if block is not None:
            blocks.append(block)

    return ASTDocument(
        source_id=source_id,
        title=title or None,
        final_url=final_url or None,
        blocks=blocks,
    )
