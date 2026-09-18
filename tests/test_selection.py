"""Unit tests for input parsing, deduplication, and interactive selection in selection.py."""

import json
from pathlib import Path
import pytest

from web_source_bundler.models import SearchResultItem
from web_source_bundler.selection import (
    deduplicate_items,
    parse_search_json,
    parse_url_file,
    select_sources_interactively,
)


def test_parse_url_file_basic(tmp_path: Path):
    file_path = tmp_path / "urls.txt"
    file_path.write_text(
        """
# This is a comment
https://example.com/page1
   https://example.com/page2   

# Another comment
https://example.com/page3

""",
        encoding="utf-8",
    )

    items = parse_url_file(file_path)
    assert len(items) == 3
    assert items[0].url == "https://example.com/page1"
    assert items[0].title is None
    assert items[0].snippet is None
    assert items[1].url == "https://example.com/page2"
    assert items[2].url == "https://example.com/page3"


def test_parse_url_file_empty_and_missing(tmp_path: Path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("\n\n# only comments\n   # indented\n", encoding="utf-8")
    assert parse_url_file(empty_file) == []

    with pytest.raises(FileNotFoundError):
        parse_url_file(tmp_path / "non_existent.txt")


def test_parse_search_json_array(tmp_path: Path):
    json_path = tmp_path / "search.json"
    data = [
        {
            "title": "Example One",
            "url": "https://example.com/1",
            "snippet": "Snippet 1 text...",
        },
        {
            "title": "Example Two (using link)",
            "link": "https://example.com/2",
            "snippet": "Snippet 2 text...",
        },
        {
            "link": "https://example.com/3",
        },
    ]
    json_path.write_text(json.dumps(data), encoding="utf-8")

    items = parse_search_json(json_path)
    assert len(items) == 3
    assert items[0].title == "Example One"
    assert items[0].url == "https://example.com/1"
    assert items[0].snippet == "Snippet 1 text..."

    assert items[1].title == "Example Two (using link)"
    assert items[1].url == "https://example.com/2"

    assert items[2].title is None
    assert items[2].url == "https://example.com/3"
    assert items[2].snippet is None


def test_parse_search_json_wrapped_dict(tmp_path: Path):
    json_path = tmp_path / "wrapped.json"
    data = {
        "results": [
            {"title": "Item A", "url": "https://a.com"},
            {"title": "Item B", "link": "https://b.com"},
        ]
    }
    json_path.write_text(json.dumps(data), encoding="utf-8")

    items = parse_search_json(json_path)
    assert len(items) == 2
    assert items[0].url == "https://a.com"
    assert items[1].url == "https://b.com"

    # Test with 'items' key
    json_path2 = tmp_path / "items_wrapped.json"
    json_path2.write_text(
        json.dumps({"items": [{"url": "https://c.com"}]}), encoding="utf-8"
    )
    items2 = parse_search_json(json_path2)
    assert len(items2) == 1
    assert items2[0].url == "https://c.com"


def test_parse_search_json_errors_and_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        parse_search_json(tmp_path / "missing.json")

    invalid_dict = tmp_path / "invalid.json"
    invalid_dict.write_text(json.dumps({"unknown_key": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a 'results' or 'items' array"):
        parse_search_json(invalid_dict)


def test_deduplicate_items():
    raw_items = [
        SearchResultItem(url="https://example.com/page", title="Page 1"),
        SearchResultItem(url="https://EXAMPLE.com/page/", title="Page 1 Duplicate"),
        SearchResultItem(url="https://example.com/other", title="Page 2"),
        SearchResultItem(url="https://example.com/page", title="Page 1 Exact Dup"),
    ]

    deduped = deduplicate_items(raw_items)
    assert len(deduped) == 2
    assert deduped[0].url == "https://example.com/page"
    assert deduped[0].title == "Page 1"
    assert deduped[1].url == "https://example.com/other"
    assert deduped[1].title == "Page 2"

    assert deduplicate_items([]) == []


def test_select_sources_interactively():
    items = [
        SearchResultItem(
            title="First Item",
            url="https://example.com/1",
            snippet="First snippet",
        ),
        SearchResultItem(
            title=None,
            url="https://example.com/2",
            snippet=None,
        ),
        SearchResultItem(
            title="Third Item",
            url="https://example.com/3",
            snippet="Third snippet",
        ),
    ]

    responses = ["y", "n", ""]
    prompts_captured = []

    def mock_prompt(prompt_str: str) -> str:
        prompts_captured.append(prompt_str)
        return responses.pop(0)

    results = select_sources_interactively(items, prompt_func=mock_prompt)

    assert len(results) == 3
    assert len(prompts_captured) == 3

    # Check prompt formats
    assert "[1] First Item\n  https://example.com/1\n  First snippet\n Include this source? [Y/n]: " in prompts_captured[0]
    assert "[2] (No title)\n  https://example.com/2\n Include this source? [Y/n]: " in prompts_captured[1]

    # Check selection outcomes
    assert results[0][0] == items[0]
    assert results[0][1] is True
    assert results[0][2] is None

    assert results[1][0] == items[1]
    assert results[1][1] is False
    assert results[1][2] == "Excluded by user during interactive selection"

    assert results[2][0] == items[2]
    assert results[2][1] is True
    assert results[2][2] is None
