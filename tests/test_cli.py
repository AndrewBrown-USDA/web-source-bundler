"""Unit tests for web-source-bundler CLI interface."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from web_source_bundler import __version__
from web_source_bundler.capture import CaptureResult
from web_source_bundler.cli import app
from web_source_bundler.models import SourceError

runner = CliRunner()


def _dummy_capture_result(url: str = "https://example.com"):
    return CaptureResult(
        final_url=url,
        title="Example Title",
        http_status=200,
        content_type="text/html",
        rendered_html="<html><body><main><h1>Hello World</h1><p>Test content.</p></main></body></html>",
        raw_html="<html><body><main><h1>Hello World</h1><p>Test content.</p></main></body></html>",
        screenshot_bytes=b"\x89PNG\r\n\x1a\nFakeScreenshotBytes",
        pdf_bytes=b"%PDF-1.4 FakePDFBytes",
        response_headers={"content-type": "text/html; charset=utf-8"},
        errors=[],
    )


def test_cli_version():
    """Verify --version flag outputs version and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"web-source-bundler version {__version__}" in result.output


def test_cli_help():
    """Verify help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "urls" in result.output
    assert "file" in result.output
    assert "search-results" in result.output


@patch("web_source_bundler.cli.run_capture")
def test_cli_urls_single_success(mock_run_capture, tmp_path: Path):
    """Test capturing a single URL from CLI."""
    mock_run_capture.return_value = _dummy_capture_result("https://example.com/page1")
    out_dir = tmp_path / "custom_bundle"

    result = runner.invoke(
        app,
        [
            "urls",
            "https://example.com/page1",
            "--out",
            str(out_dir),
            "--include-links-table",
        ],
    )

    assert result.exit_code == 0
    assert mock_run_capture.called
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "combined.md").exists()
    assert (out_dir / "checksums.sha256").exists()
    assert (out_dir / "sources" / "001" / "readable.md").exists()
    assert "Bundle Execution Summary" in result.output
    assert "001" in result.output


@patch("web_source_bundler.cli.run_capture")
def test_cli_urls_multiple_deduplicated(mock_run_capture, tmp_path: Path):
    """Test capturing multiple URLs with duplicate normalization."""
    mock_run_capture.return_value = _dummy_capture_result("https://example.com/page1")
    out_dir = tmp_path / "custom_bundle"

    result = runner.invoke(
        app,
        [
            "urls",
            "https://example.com/page1",
            "HTTPS://example.com/page1/",
            "https://example.com/page2",
            "-o",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    # Should only capture 2 unique URLs
    assert mock_run_capture.call_count == 2
    assert (out_dir / "sources" / "001").exists()
    assert (out_dir / "sources" / "002").exists()
    assert not (out_dir / "sources" / "003").exists()


@patch("web_source_bundler.cli.run_capture")
def test_cli_file_command(mock_run_capture, tmp_path: Path):
    """Test the 'file' command with a text file input."""
    mock_run_capture.return_value = _dummy_capture_result("https://example.com/file-target")
    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "# Comment line\nhttps://example.com/file-target\n\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "file_bundle"

    result = runner.invoke(
        app,
        ["file", str(url_file), "-o", str(out_dir), "--no-screenshot", "--no-pdf"],
    )

    assert result.exit_code == 0
    assert mock_run_capture.called
    _, kwargs = mock_run_capture.call_args
    assert kwargs.get("save_screenshot") is False
    assert kwargs.get("save_pdf") is False
    assert (out_dir / "manifest.json").exists()


@patch("web_source_bundler.cli.run_capture")
def test_cli_search_results_command(mock_run_capture, tmp_path: Path):
    """Test the 'search-results' command with a JSON file input."""
    mock_run_capture.return_value = _dummy_capture_result("https://example.com/search-hit")
    json_file = tmp_path / "results.json"
    json_data = [
        {
            "title": "Search Hit Title",
            "url": "https://example.com/search-hit",
            "snippet": "This is a search result snippet.",
        }
    ]
    json_file.write_text(json.dumps(json_data), encoding="utf-8")
    out_dir = tmp_path / "json_bundle"

    result = runner.invoke(
        app,
        [
            "search-results",
            str(json_file),
            "-o",
            str(out_dir),
            "--include-raw-html",
            "--redact-pattern",
            "secret[0-9]+",
        ],
    )

    assert result.exit_code == 0
    assert mock_run_capture.called
    _, kwargs = mock_run_capture.call_args
    assert kwargs.get("save_raw_html") is True
    assert (out_dir / "manifest.json").exists()


@patch("web_source_bundler.cli.select_sources_interactively")
@patch("web_source_bundler.cli.run_capture")
def test_cli_interactive_filtering(mock_run_capture, mock_interactive, tmp_path: Path):
    """Test interactive selection where user includes one source and excludes another."""
    from web_source_bundler.models import SearchResultItem

    mock_run_capture.return_value = _dummy_capture_result("https://example.com/kept")
    item1 = SearchResultItem(url="https://example.com/kept", title="Kept")
    item2 = SearchResultItem(url="https://example.com/skipped", title="Skipped")

    # Mock interactive selector returning (item, selected, note)
    mock_interactive.return_value = [
        (item1, True, None),
        (item2, False, "Excluded by user during interactive selection"),
    ]

    out_dir = tmp_path / "interactive_bundle"

    result = runner.invoke(
        app,
        [
            "urls",
            "https://example.com/kept",
            "https://example.com/skipped",
            "-o",
            str(out_dir),
            "--interactive",
        ],
    )

    assert result.exit_code == 0
    assert mock_interactive.called
    # run_capture should only be called once for the included item
    assert mock_run_capture.call_count == 1
    assert (out_dir / "sources" / "001" / "readable.md").exists()
    assert (out_dir / "sources" / "002" / "metadata.json").exists()
    assert not (out_dir / "sources" / "002" / "readable.md").exists()

    manifest_data = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest_data["sources"]) == 2
    assert manifest_data["sources"][0]["selected"] is True
    assert manifest_data["sources"][1]["selected"] is False
    assert manifest_data["sources"][1]["selection_note"] == "Excluded by user during interactive selection"


@patch("web_source_bundler.cli.run_capture")
def test_cli_capture_with_errors(mock_run_capture, tmp_path: Path):
    """Test handling of capture warnings/errors in CLI output and summary table."""
    from datetime import datetime, timezone

    error_result = CaptureResult(
        final_url="https://example.com/failed",
        title="Failed Page",
        errors=[
            SourceError(
                stage="capture_navigation",
                message="Timeout 30000ms exceeded",
                timestamp=datetime.now(timezone.utc),
            )
        ],
    )
    mock_run_capture.return_value = error_result
    out_dir = tmp_path / "error_bundle"

    result = runner.invoke(
        app,
        ["urls", "https://example.com/failed", "-o", str(out_dir)],
    )

    assert result.exit_code == 0
    assert "Captured with 1 warning(s)/error(s)" in result.output
    assert "Warnings" in result.output
    assert (out_dir / "manifest.json").exists()
