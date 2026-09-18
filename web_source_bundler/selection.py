"""Input parsing, deduplication, and interactive source selection routines."""

import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

from web_source_bundler.models import SearchResultItem
from web_source_bundler.utils import normalize_url


def parse_url_file(file_path: Union[str, Path]) -> List[SearchResultItem]:
    """Parse a plain text file containing URLs.
    
    Ignores empty lines, whitespace-only lines, and lines starting with `#` comments.
    Wraps valid lines into SearchResultItem(url=..., title=None, snippet=None).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"URL file not found: {path}")

    items: List[SearchResultItem] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            items.append(SearchResultItem(url=stripped, title=None, snippet=None))

    return items


def parse_search_json(file_path: Union[str, Path]) -> List[SearchResultItem]:
    """Parse a JSON file containing search results.
    
    Accepts either a top-level JSON array of result objects or a JSON object with a
    'results' or 'items' list. Supports 'url' or 'link' keys for the URL, and optional
    'title' and 'snippet' fields.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Search JSON file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_items = []
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            raw_items = data["results"]
        elif "items" in data and isinstance(data["items"], list):
            raw_items = data["items"]
        else:
            raise ValueError("Search JSON object must contain a 'results' or 'items' array")
    else:
        raise ValueError("Invalid Search JSON format: root must be a list or object")

    items: List[SearchResultItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        url = raw.get("url") or raw.get("link")
        if not url or not isinstance(url, str):
            continue
        title = raw.get("title")
        snippet = raw.get("snippet")
        items.append(
            SearchResultItem(
                url=url.strip(),
                title=str(title).strip() if title is not None else None,
                snippet=str(snippet).strip() if snippet is not None else None,
            )
        )

    return items


def deduplicate_items(items: List[SearchResultItem]) -> List[SearchResultItem]:
    """Deduplicate a list of SearchResultItem objects by normalized URL, preserving first-seen order."""
    seen_urls = set()
    deduped: List[SearchResultItem] = []

    for item in items:
        norm = normalize_url(item.url)
        if norm not in seen_urls:
            seen_urls.add(norm)
            deduped.append(item)

    return deduped


def select_sources_interactively(
    items: List[SearchResultItem],
    prompt_func: Optional[Callable[[str], str]] = None,
) -> List[Tuple[SearchResultItem, bool, Optional[str]]]:
    """Present each candidate source for interactive selection.
    
    Displays:
      [i] Title
        URL
        Snippet
      Include this source? [Y/n]:
    
    Default is True ('Y'/'y'/empty).
    Returns list of (item, selected, selection_note) tuples.
    """
    if prompt_func is None:
        prompt_func = input

    results: List[Tuple[SearchResultItem, bool, Optional[str]]] = []

    for idx, item in enumerate(items, start=1):
        title_str = item.title if item.title else "(No title)"
        snippet_str = f"  {item.snippet}\n" if item.snippet else ""
        prompt_msg = (
            f"[{idx}] {title_str}\n"
            f"  {item.url}\n"
            f"{snippet_str}"
            f" Include this source? [Y/n]: "
        )

        user_input = prompt_func(prompt_msg)
        cleaned_input = user_input.strip().lower() if user_input else ""

        if cleaned_input in ("", "y", "yes"):
            selected = True
            note = None
        else:
            selected = False
            note = "Excluded by user during interactive selection"

        results.append((item, selected, note))

    return results
