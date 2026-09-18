"""Unit tests for source_bundler.bundle.BundlePackager."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional
import pytest

from source_bundler.bundle import BundlePackager
from source_bundler.models import CaptureConfig, Manifest, SourceError, SourceRecord


@dataclass
class MockCaptureResult:
    """Mock capture result conforming to Playwright capture output."""
    final_url: Optional[str] = "https://example.com/final"
    title: Optional[str] = "Example Domain"
    http_status: Optional[int] = 200
    content_type: Optional[str] = "text/html; charset=utf-8"
    rendered_html: Optional[str] = (
        "<!DOCTYPE html><html><head><title>Example Domain</title></head>"
        "<body><h1>Example Domain</h1><p>This is an example paragraph with a "
        "<a href=\"https://example.com/more\">link</a>.</p></body></html>"
    )
    raw_html: Optional[str] = "<html><body>Raw HTML</body></html>"
    screenshot_bytes: Optional[bytes] = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."
    pdf_bytes: Optional[bytes] = b"%PDF-1.4 mock pdf data"
    response_headers: Dict[str, str] = field(default_factory=lambda: {"content-type": "text/html", "server": "mock"})
    errors: List[SourceError] = field(default_factory=list)


def test_bundle_packager_init_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BundlePackager initialization with default auto-generated directory."""
    monkeypatch.chdir(tmp_path)
    packager = BundlePackager()
    
    assert packager.bundle_id.startswith("source-bundle-")
    assert packager.out_dir.exists()
    assert (packager.out_dir / "sources").exists()
    assert isinstance(packager.config, CaptureConfig)
    assert len(packager.sources) == 0


def test_bundle_packager_init_custom_out_dir(tmp_path: Path) -> None:
    """Test BundlePackager initialization with explicit output directory."""
    out_dir = tmp_path / "custom_bundle"
    custom_config = CaptureConfig(locale="fr-FR", timezone="Europe/Paris")
    packager = BundlePackager(out_dir=out_dir, config=custom_config)

    assert packager.out_dir == out_dir
    assert out_dir.exists()
    assert (out_dir / "sources").exists()
    assert packager.config.locale == "fr-FR"


def test_add_source_success(tmp_path: Path) -> None:
    """Test adding a successfully captured source with full artifacts."""
    out_dir = tmp_path / "test_bundle"
    packager = BundlePackager(out_dir=out_dir)

    mock_result = MockCaptureResult()
    record = packager.add_source(
        source_id="001",
        input_url="https://example.com",
        capture_result=mock_result,
        selected=True,
        selection_note="Primary reference",
    )

    assert isinstance(record, SourceRecord)
    assert record.source_id == "001"
    assert record.input_url == "https://example.com"
    assert record.final_url == "https://example.com/final"
    assert record.title == "Example Domain"
    assert record.http_status == 200
    assert record.selected is True
    assert record.selection_note == "Primary reference"

    # Verify source directory and files on disk
    src_dir = out_dir / "sources" / "001"
    assert (src_dir / "rendered.html").is_file()
    assert (src_dir / "ast.json").is_file()
    assert (src_dir / "readable.md").is_file()
    assert (src_dir / "screenshot.png").is_file()
    assert (src_dir / "page.pdf").is_file()
    assert (src_dir / "metadata.json").is_file()

    # Raw HTML & headers should not be written by default
    assert not (src_dir / "raw.html").exists()
    assert not (src_dir / "response_headers.json").exists()

    # Check artifact refs POSIX paths
    assert record.artifacts.rendered_html == "sources/001/rendered.html"
    assert record.artifacts.readable_markdown == "sources/001/readable.md"
    assert record.artifacts.ast_json == "sources/001/ast.json"
    assert record.artifacts.screenshot == "sources/001/screenshot.png"
    assert record.artifacts.pdf == "sources/001/page.pdf"
    assert record.artifacts.raw_html is None

    # Check hashes dictionary
    assert "rendered_html" in record.hashes
    assert "readable_markdown" in record.hashes
    assert "ast_json" in record.hashes
    assert "screenshot" in record.hashes
    assert "pdf" in record.hashes
    assert record.hashes["rendered_html"].startswith("sha256:")

    # Verify metadata.json content matches SourceRecord
    metadata_content = (src_dir / "metadata.json").read_text(encoding="utf-8")
    loaded_record = SourceRecord.model_validate_json(metadata_content)
    assert loaded_record.source_id == "001"
    assert loaded_record.hashes == record.hashes

    # Verify ast.json content
    ast_data = json.loads((src_dir / "ast.json").read_text(encoding="utf-8"))
    assert ast_data["source_id"] == "001"
    assert len(ast_data["blocks"]) > 0


def test_add_source_with_raw_html_and_headers(tmp_path: Path) -> None:
    """Test adding a source with include_raw_html enabled."""
    out_dir = tmp_path / "raw_bundle"
    packager = BundlePackager(out_dir=out_dir, include_raw_html=True)

    mock_result = MockCaptureResult()
    record = packager.add_source(
        source_id="002",
        input_url="https://example.com/raw",
        capture_result=mock_result,
    )

    src_dir = out_dir / "sources" / "002"
    assert (src_dir / "raw.html").is_file()
    assert (src_dir / "response_headers.json").is_file()
    assert record.artifacts.raw_html == "sources/002/raw.html"
    assert record.artifacts.response_headers == "sources/002/response_headers.json"
    assert "raw_html" in record.hashes
    assert "response_headers" in record.hashes


def test_add_source_redaction_and_links_table(tmp_path: Path) -> None:
    """Test adding a source with redaction patterns and include_links_table enabled."""
    out_dir = tmp_path / "redact_bundle"
    packager = BundlePackager(
        out_dir=out_dir,
        redact_patterns=[r"example paragraph"],
        include_links_table=True,
    )

    mock_result = MockCaptureResult()
    packager.add_source(
        source_id="003",
        input_url="https://example.com/redacted",
        capture_result=mock_result,
    )

    readable_md = (out_dir / "sources" / "003" / "readable.md").read_text(encoding="utf-8")
    assert "[REDACTED]" in readable_md
    assert "example paragraph" not in readable_md
    assert "### Extracted Links" in readable_md
    assert "https://example.com/more" in readable_md


def test_add_source_failure(tmp_path: Path) -> None:
    """Test adding a source that encountered capture errors."""
    out_dir = tmp_path / "error_bundle"
    packager = BundlePackager(out_dir=out_dir)

    mock_error = SourceError(
        stage="capture",
        message="Navigation timeout exceeded 30000ms",
        timestamp=packager.created_at,
    )
    mock_result = MockCaptureResult(
        final_url=None,
        title=None,
        http_status=None,
        content_type=None,
        rendered_html=None,
        raw_html=None,
        screenshot_bytes=None,
        pdf_bytes=None,
        errors=[mock_error],
    )

    record = packager.add_source(
        source_id="004",
        input_url="https://timeout.example.com",
        capture_result=mock_result,
    )

    assert len(record.errors) == 1
    assert record.errors[0].stage == "capture"
    assert "timeout" in record.errors[0].message

    src_dir = out_dir / "sources" / "004"
    assert (src_dir / "metadata.json").is_file()
    assert not (src_dir / "rendered.html").exists()
    assert not (src_dir / "readable.md").exists()


def test_finalize_bundle(tmp_path: Path) -> None:
    """Test finalizing a bundle: manifest.json, combined.md, and checksums.sha256."""
    out_dir = tmp_path / "final_bundle"
    packager = BundlePackager(out_dir=out_dir)

    mock_result_1 = MockCaptureResult(title="Page One")
    mock_result_2 = MockCaptureResult(
        title="Page Two",
        rendered_html="<html><body><h1>Second Page</h1><p>Some text</p></body></html>",
    )

    packager.add_source("001", "https://example.com/1", mock_result_1)
    packager.add_source("002", "https://example.com/2", mock_result_2)

    bundle_path = packager.finalize()
    assert bundle_path == out_dir

    # 1. Manifest
    manifest_path = out_dir / "manifest.json"
    assert manifest_path.is_file()
    manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.bundle_id == packager.bundle_id
    assert len(manifest.sources) == 2
    assert manifest.sources[0].source_id == "001"
    assert manifest.sources[1].source_id == "002"

    # 2. Combined markdown
    combined_path = out_dir / "combined.md"
    assert combined_path.is_file()
    combined_md = combined_path.read_text(encoding="utf-8")
    assert "# Source Bundle" in combined_md
    assert f"Bundle ID: {packager.bundle_id}" in combined_md
    assert "## Source 001: Page One" in combined_md
    assert "## Source 002: Page Two" in combined_md

    # 3. Checksums file
    checksums_path = out_dir / "checksums.sha256"
    assert checksums_path.is_file()
    checksums_text = checksums_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in checksums_text.splitlines() if line.strip()]

    # Ensure POSIX formatting and presence of all generated files
    assert any("  manifest.json" in line for line in lines)
    assert any("  combined.md" in line for line in lines)
    assert any("  sources/001/rendered.html" in line for line in lines)
    assert any("  sources/001/metadata.json" in line for line in lines)
    assert any("  sources/002/readable.md" in line for line in lines)
    assert not any("checksums.sha256" in line for line in lines)

    # Check checksum formatting: <hex>  <relpath>
    for line in lines:
        parts = line.split("  ")
        assert len(parts) == 2
        assert len(parts[0]) == 64  # SHA-256 hex length
        assert not parts[0].startswith("sha256:")
        assert "\\" not in parts[1]  # Strict POSIX slashes
