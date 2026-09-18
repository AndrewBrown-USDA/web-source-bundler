"""Unit tests for hashing utilities in source_bundler.hashing."""

import hashlib
from pathlib import Path
import pytest
from source_bundler.hashing import (
    hash_bytes,
    hash_string,
    hash_file,
    generate_checksums_content,
)

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
HELLO_SHA256 = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_hash_bytes():
    assert hash_bytes(b"") == f"sha256:{EMPTY_SHA256}"
    assert hash_bytes(b"hello world") == f"sha256:{HELLO_SHA256}"


def test_hash_string():
    assert hash_string("") == f"sha256:{EMPTY_SHA256}"
    assert hash_string("hello world") == f"sha256:{HELLO_SHA256}"
    # Unicode test
    unicode_text = "Python 3.14 — 日本語 & Café 🚀"
    expected = hashlib.sha256(unicode_text.encode("utf-8")).hexdigest()
    assert hash_string(unicode_text) == f"sha256:{expected}"


def test_hash_file(tmp_path: Path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello world", encoding="utf-8")
    assert hash_file(test_file) == f"sha256:{HELLO_SHA256}"
    # Test path as string
    assert hash_file(str(test_file)) == f"sha256:{HELLO_SHA256}"


def test_hash_file_large_streaming(tmp_path: Path):
    large_file = tmp_path / "large.bin"
    # Create 200KB of repeating data (exceeds default 64KB chunk size)
    data = b"0123456789ABCDEF" * 12800
    large_file.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    assert hash_file(large_file, chunk_size=1024) == f"sha256:{expected}"


def test_generate_checksums_content():
    file_hashes = {
        "sources/002/readable.md": f"sha256:{HELLO_SHA256}",
        "sources/001/rendered.html": EMPTY_SHA256,
        "manifest.json": f"sha256:{HELLO_SHA256}",
    }

    content = generate_checksums_content(file_hashes)
    lines = content.splitlines()

    assert len(lines) == 3
    # Check alphabetical ordering by path
    assert lines[0] == f"{HELLO_SHA256}  manifest.json"
    assert lines[1] == f"{EMPTY_SHA256}  sources/001/rendered.html"
    assert lines[2] == f"{HELLO_SHA256}  sources/002/readable.md"
    assert content.endswith("\n")


def test_generate_checksums_content_windows_paths():
    file_hashes = {
        r"sources\001\screenshot.png": f"sha256:{HELLO_SHA256}",
        r"sources\002\page.pdf": f"sha256:{EMPTY_SHA256}",
    }

    content = generate_checksums_content(file_hashes)
    lines = content.splitlines()

    assert len(lines) == 2
    assert lines[0] == f"{HELLO_SHA256}  sources/001/screenshot.png"
    assert lines[1] == f"{EMPTY_SHA256}  sources/002/page.pdf"
