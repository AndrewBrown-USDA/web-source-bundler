"""Deterministic Playwright-based web page capture."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from web_source_bundler.models import (
    DEFAULT_USER_AGENT,
    CaptureConfig,
    SourceError,
    ViewportConfig,
)


class CaptureResult(BaseModel):
    """Result of capturing a single web page via Playwright."""
    final_url: Optional[str] = None
    title: Optional[str] = None
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    rendered_html: Optional[str] = None
    raw_html: Optional[str] = None
    screenshot_bytes: Optional[bytes] = None
    pdf_bytes: Optional[bytes] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    errors: List[SourceError] = Field(default_factory=list)


def _get_default_config() -> CaptureConfig:
    """Return standard deterministic capture configuration."""
    return CaptureConfig(
        viewport=ViewportConfig(width=1365, height=768),
        locale="en-US",
        timezone="UTC",
        user_agent=DEFAULT_USER_AGENT,
        timeout_seconds=30,
    )


async def capture_url(
    url: str,
    config: Optional[CaptureConfig] = None,
    save_screenshot: bool = True,
    save_pdf: bool = True,
    save_raw_html: bool = False,
) -> CaptureResult:
    """Capture a URL asynchronously using headless Chromium via Playwright.

    Renders the page, extracts final URL, title, HTTP status,
    DOM HTML, screenshot, PDF printout, and optional raw response HTML.
    Records errors in CaptureResult.errors.
    """
    if config is None:
        config = _get_default_config()

    result = CaptureResult()
    timeout_ms = config.timeout_seconds * 1000

    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        result.errors.append(
            SourceError(
                stage="capture",
                message=f"Playwright is not installed: {e}",
                timestamp=datetime.now(timezone.utc),
            )
        )
        return result

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                # Configure deterministic isolated context
                context_kwargs = {
                    "viewport": {
                        "width": config.viewport.width,
                        "height": config.viewport.height,
                    },
                    "locale": config.locale,
                    "timezone_id": config.timezone,
                    "user_agent": config.user_agent,
                    "java_script_enabled": True,
                    "ignore_https_errors": True,
                    "accept_downloads": False,
                }

                # Try to block service workers via context options if supported
                try:
                    context = await browser.new_context(
                        **context_kwargs,
                        service_workers="block",
                    )
                except (TypeError, Exception):
                    context = await browser.new_context(**context_kwargs)

                # Route handler to abort service worker registrations/scripts
                async def _block_sw_route(route):
                    req = route.request
                    if req.resource_type == "serviceworker" or "service-worker" in req.url:
                        await route.abort()
                    else:
                        await route.continue_()

                try:
                    await context.route("**/*", _block_sw_route)
                except Exception:
                    pass

                page = await context.new_page()
                page.set_default_timeout(timeout_ms)

                # Capture raw response body if requested
                raw_body_bytes: Optional[bytes] = None

                # Navigate with domcontentloaded
                response = None
                try:
                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                except Exception as nav_err:
                    result.errors.append(
                        SourceError(
                            stage="capture_navigation",
                            message=str(nav_err),
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                # Record response details if available
                if response is not None:
                    try:
                        result.http_status = response.status
                        headers = await response.all_headers()
                        result.response_headers = {str(k).lower(): str(v) for k, v in headers.items()}
                        result.content_type = result.response_headers.get("content-type")
                        if save_raw_html:
                            try:
                                raw_body_bytes = await response.body()
                                result.raw_html = raw_body_bytes.decode("utf-8", errors="replace")
                            except Exception as raw_err:
                                result.errors.append(
                                    SourceError(
                                        stage="capture_raw_html",
                                        message=str(raw_err),
                                        timestamp=datetime.now(timezone.utc),
                                    )
                                )
                    except Exception as resp_err:
                        result.errors.append(
                            SourceError(
                                stage="capture_response",
                                message=str(resp_err),
                                timestamp=datetime.now(timezone.utc),
                            )
                        )

                # Attempt short wait for networkidle, but do not fail if it times out
                try:
                    idle_timeout = min(5000, timeout_ms)
                    await page.wait_for_load_state("networkidle", timeout=idle_timeout)
                except Exception:
                    pass

                # Extract basic page info
                try:
                    result.final_url = page.url
                except Exception:
                    result.final_url = url

                try:
                    result.title = await page.title()
                except Exception as title_err:
                    result.errors.append(
                        SourceError(
                            stage="capture_title",
                            message=str(title_err),
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                # Extract rendered DOM HTML
                try:
                    result.rendered_html = await page.content()
                except Exception as html_err:
                    result.errors.append(
                        SourceError(
                            stage="capture_html",
                            message=str(html_err),
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                # Capture full-page screenshot
                if save_screenshot:
                    try:
                        result.screenshot_bytes = await page.screenshot(
                            full_page=True,
                            timeout=timeout_ms,
                        )
                    except Exception as ss_err:
                        result.errors.append(
                            SourceError(
                                stage="capture_screenshot",
                                message=str(ss_err),
                                timestamp=datetime.now(timezone.utc),
                            )
                        )

                # Capture PDF
                if save_pdf:
                    try:
                        result.pdf_bytes = await page.pdf(
                            print_background=True,
                            timeout=timeout_ms,
                        )
                    except Exception as pdf_err:
                        result.errors.append(
                            SourceError(
                                stage="capture_pdf",
                                message=str(pdf_err),
                                timestamp=datetime.now(timezone.utc),
                            )
                        )

                await context.close()
            finally:
                await browser.close()

    except Exception as exc:
        result.errors.append(
            SourceError(
                stage="capture",
                message=str(exc),
                timestamp=datetime.now(timezone.utc),
            )
        )

    return result


def run_capture(
    url: str,
    config: Optional[CaptureConfig] = None,
    save_screenshot: bool = True,
    save_pdf: bool = True,
    save_raw_html: bool = False,
) -> CaptureResult:
    """Synchronous wrapper for capture_url."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    coro = capture_url(
        url=url,
        config=config,
        save_screenshot=save_screenshot,
        save_pdf=save_pdf,
        save_raw_html=save_raw_html,
    )

    if loop is not None and loop.is_running():
        # Running in an existing event loop (e.g. nested / jupyter), run in a separate thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()
    else:
        return asyncio.run(coro)
