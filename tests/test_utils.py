"""Unit tests for utility functions in web_source_bundler.utils."""

from datetime import datetime, timezone, timedelta
import pytest
from web_source_bundler.utils import (
    sanitize_filename,
    format_utc_timestamp,
    generate_bundle_id,
    normalize_url,
)


def test_sanitize_filename_basic():
    assert sanitize_filename("simple-file_name123") == "simple-file_name123"
    assert sanitize_filename("Simple Title With Spaces") == "Simple-Title-With-Spaces"


def test_sanitize_filename_special_chars():
    assert sanitize_filename("hello@world#$%^&*()") == "hello-world"
    assert sanitize_filename("test:::colons???") == "test-colons"


def test_sanitize_filename_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "etc-passwd"
    assert sanitize_filename("..\\..\\Windows\\System32") == "Windows-System32"


def test_sanitize_filename_empty_and_fallback():
    assert sanitize_filename("") == "unnamed"
    assert sanitize_filename("   ") == "unnamed"
    assert sanitize_filename("???///:::***") == "unnamed"


def test_sanitize_filename_max_length():
    long_name = "a" * 150
    sanitized = sanitize_filename(long_name, max_length=50)
    assert len(sanitized) <= 50
    assert sanitized == "a" * 50

    # Truncation should not leave trailing hyphens
    long_hyphenated = "abc-" * 30
    sanitized_hyphen = sanitize_filename(long_hyphenated, max_length=10)
    assert not sanitized_hyphen.endswith("-")
    assert len(sanitized_hyphen) <= 10


def test_format_utc_timestamp_default():
    ts = format_utc_timestamp()
    assert ts.endswith("Z")
    assert "T" in ts
    # Verify parseable as ISO 8601
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert dt.tzinfo is not None


def test_format_utc_timestamp_explicit():
    dt = datetime(2026, 9, 18, 14, 30, 45, tzinfo=timezone.utc)
    assert format_utc_timestamp(dt) == "2026-09-18T14:30:45Z"

    # Test timezone conversion from non-UTC
    tz_plus_2 = timezone(timedelta(hours=2))
    dt_tz = datetime(2026, 9, 18, 16, 30, 45, tzinfo=tz_plus_2)
    assert format_utc_timestamp(dt_tz) == "2026-09-18T14:30:45Z"

    # Test naive datetime assumes UTC
    dt_naive = datetime(2026, 9, 18, 14, 30, 45)
    assert format_utc_timestamp(dt_naive) == "2026-09-18T14:30:45Z"


def test_generate_bundle_id_default():
    bundle_id = generate_bundle_id()
    assert bundle_id.startswith("source-bundle-")
    assert bundle_id.endswith("Z")
    assert len(bundle_id) == len("source-bundle-20260918T143045Z")


def test_generate_bundle_id_explicit():
    dt = datetime(2026, 9, 18, 14, 30, 45, tzinfo=timezone.utc)
    assert generate_bundle_id(dt) == "source-bundle-20260918T143045Z"


def test_normalize_url_basic():
    assert normalize_url("HTTP://EXAMPLE.COM") == "http://example.com"
    assert normalize_url("https://Example.COM/Path/To/Page") == "https://example.com/Path/To/Page"


def test_normalize_url_whitespace():
    assert normalize_url("  https://example.com/test  ") == "https://example.com/test"


def test_normalize_url_trailing_slashes():
    assert normalize_url("https://example.com/") == "https://example.com/"
    assert normalize_url("https://example.com/path/") == "https://example.com/path"
    assert normalize_url("https://example.com/path/subpath/") == "https://example.com/path/subpath"


def test_normalize_url_ports():
    assert normalize_url("http://example.com:80/page") == "http://example.com/page"
    assert normalize_url("https://example.com:443/page") == "https://example.com/page"
    assert normalize_url("http://example.com:8080/page") == "http://example.com:8080/page"


def test_normalize_url_query_and_fragment():
    assert normalize_url("https://example.com/page/?q=1#section") == "https://example.com/page?q=1#section"


def test_normalize_url_empty():
    assert normalize_url("") == ""
    assert normalize_url("   ") == ""
