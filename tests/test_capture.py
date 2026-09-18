"""Unit tests for Playwright browser capture module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from web_source_bundler.capture import (
    DEFAULT_USER_AGENT,
    CaptureResult,
    _get_default_config,
    capture_url,
    run_capture,
)
from web_source_bundler.models import CaptureConfig, SourceError, ViewportConfig


def test_capture_result_defaults():
    """Test default values of CaptureResult model."""
    result = CaptureResult()
    assert result.final_url is None
    assert result.title is None
    assert result.http_status is None
    assert result.content_type is None
    assert result.rendered_html is None
    assert result.raw_html is None
    assert result.screenshot_bytes is None
    assert result.pdf_bytes is None
    assert result.response_headers == {}
    assert result.errors == []


def test_get_default_config():
    """Test default capture configuration values match requirements."""
    cfg = _get_default_config()
    assert cfg.viewport.width == 1365
    assert cfg.viewport.height == 768
    assert cfg.locale == "en-US"
    assert cfg.timezone == "UTC"
    assert cfg.user_agent == DEFAULT_USER_AGENT
    assert cfg.timeout_seconds == 30


def test_capture_url_success():
    """Test successful capture_url with all artifacts enabled."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.all_headers = AsyncMock(return_value={"Content-Type": "text/html; charset=utf-8", "Server": "nginx"})
    mock_response.body = AsyncMock(return_value=b"<html>Raw Content</html>")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.url = "https://example.com/final"
    mock_page.title = AsyncMock(return_value="Example Final Page")
    mock_page.content = AsyncMock(return_value="<html><body><h1>Example Final Page</h1></body></html>")
    mock_page.screenshot = AsyncMock(return_value=b"fake-png-screenshot")
    mock_page.pdf = AsyncMock(return_value=b"fake-pdf-bytes")
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.route = AsyncMock()
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_cm = AsyncMock()
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright_cm.__aenter__.return_value = mock_playwright
    mock_playwright_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
        res = asyncio.run(
            capture_url(
                "https://example.com",
                save_screenshot=True,
                save_pdf=True,
                save_raw_html=True,
            )
        )

    assert res.final_url == "https://example.com/final"
    assert res.title == "Example Final Page"
    assert res.http_status == 200
    assert res.content_type == "text/html; charset=utf-8"
    assert res.rendered_html == "<html><body><h1>Example Final Page</h1></body></html>"
    assert res.raw_html == "<html>Raw Content</html>"
    assert res.screenshot_bytes == b"fake-png-screenshot"
    assert res.pdf_bytes == b"fake-pdf-bytes"
    assert res.response_headers["server"] == "nginx"
    assert len(res.errors) == 0


def test_capture_url_flags_disabled():
    """Test capture_url with screenshot, PDF, and raw HTML disabled."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.all_headers = AsyncMock(return_value={"Content-Type": "text/html"})
    mock_response.body = AsyncMock(return_value=b"<html>Raw</html>")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Example Page")
    mock_page.content = AsyncMock(return_value="<html>Rendered</html>")
    mock_page.screenshot = AsyncMock()
    mock_page.pdf = AsyncMock()
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.route = AsyncMock()
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_cm = AsyncMock()
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright_cm.__aenter__.return_value = mock_playwright
    mock_playwright_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
        res = asyncio.run(
            capture_url(
                "https://example.com",
                save_screenshot=False,
                save_pdf=False,
                save_raw_html=False,
            )
        )

    assert res.screenshot_bytes is None
    assert res.pdf_bytes is None
    assert res.raw_html is None
    assert res.rendered_html == "<html>Rendered</html>"
    mock_page.screenshot.assert_not_called()
    mock_page.pdf.assert_not_called()
    mock_response.body.assert_not_called()


def test_capture_url_navigation_error():
    """Test non-fatal capture navigation error handling."""
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(side_effect=Exception("net::ERR_NAME_NOT_RESOLVED"))
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.url = "https://invalid-non-existent-domain.xyz"
    mock_page.title = AsyncMock(return_value="")
    mock_page.content = AsyncMock(return_value="")
    mock_page.screenshot = AsyncMock(side_effect=Exception("Cannot screenshot empty page"))
    mock_page.pdf = AsyncMock(side_effect=Exception("Cannot generate PDF"))
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.route = AsyncMock()
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_cm = AsyncMock()
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright_cm.__aenter__.return_value = mock_playwright
    mock_playwright_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
        res = asyncio.run(capture_url("https://invalid-non-existent-domain.xyz"))

    assert res.http_status is None
    assert len(res.errors) >= 1
    assert any(e.stage == "capture_navigation" for e in res.errors)


def test_capture_url_browser_launch_failure():
    """Test non-fatal error handling when browser launch fails entirely."""
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(side_effect=RuntimeError("Chromium binary not found"))
    mock_playwright_cm = AsyncMock()
    mock_playwright_cm.__aenter__.return_value = mock_playwright
    mock_playwright_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
        res = asyncio.run(capture_url("https://example.com"))

    assert len(res.errors) == 1
    assert res.errors[0].stage == "capture"
    assert "Chromium binary not found" in res.errors[0].message


def test_run_capture_sync():
    """Test synchronous run_capture helper."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.all_headers = AsyncMock(return_value={"Content-Type": "text/html"})

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Sync Example")
    mock_page.content = AsyncMock(return_value="<html>Sync</html>")
    mock_page.screenshot = AsyncMock(return_value=b"sync-screenshot")
    mock_page.pdf = AsyncMock(return_value=b"sync-pdf")
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.route = AsyncMock()
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_cm = AsyncMock()
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright_cm.__aenter__.return_value = mock_playwright
    mock_playwright_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
        res = run_capture(
            "https://example.com",
            save_screenshot=True,
            save_pdf=True,
        )

    assert res.final_url == "https://example.com"
    assert res.title == "Sync Example"
    assert res.http_status == 200
    assert res.rendered_html == "<html>Sync</html>"
    assert res.screenshot_bytes == b"sync-screenshot"
    assert res.pdf_bytes == b"sync-pdf"
    assert len(res.errors) == 0
