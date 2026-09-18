"""Command line interface for web-source-bundler."""

from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table

from web_source_bundler import __version__
from web_source_bundler.bundle import BundlePackager
from web_source_bundler.capture import CaptureResult, run_capture
from web_source_bundler.models import CaptureConfig, SearchResultItem
from web_source_bundler.selection import (
    deduplicate_items,
    parse_search_json,
    parse_url_file,
    select_sources_interactively,
)

app = typer.Typer(
    name="web-source-bundler",
    help="Deterministic web source capture and AI-assisted research packaging tool.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    """Print tool version and exit."""
    if value:
        console.print(f"web-source-bundler version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """web-source-bundler top-level CLI callback."""
    pass


def _execute_bundling(
    items: List[SearchResultItem],
    out: Optional[Path],
    interactive: bool,
    screenshot: bool,
    pdf: bool,
    include_raw_html: bool,
    include_links_table: bool,
    redact_pattern: Optional[List[str]],
    timeout: int,
) -> Path:
    """Core orchestration pipeline for processing items into a bundle."""
    # 1. Deduplicate items by URL
    deduped = deduplicate_items(items)
    if not deduped:
        console.print("[yellow]No valid URLs found to bundle.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[bold cyan]Discovered {len(deduped)} unique source(s) to process.[/bold cyan]")

    # 2. Interactive selection if enabled
    if interactive:
        selected_pairs = select_sources_interactively(deduped)
    else:
        selected_pairs = [(item, True, None) for item in deduped]

    # 3. Setup configuration & packager
    config = CaptureConfig(timeout_seconds=timeout)
    packager = BundlePackager(
        out_dir=out,
        config=config,
        redact_patterns=redact_pattern,
        include_links_table=include_links_table,
        include_raw_html=include_raw_html,
    )

    # 4. Process each source
    for idx, (item, is_selected, note) in enumerate(selected_pairs, start=1):
        source_id = f"{idx:03d}"
        if not is_selected:
            console.print(f"[dim]• [{source_id}] Excluded: {item.url}[/dim]")
            dummy_result = CaptureResult(title=item.title)
            packager.add_source(
                source_id=source_id,
                input_url=item.url,
                capture_result=dummy_result,
                selected=False,
                selection_note=note,
            )
            continue

        with console.status(f"[bold blue]Capturing [{source_id}] {item.url}...[/bold blue]"):
            capture_res = run_capture(
                url=item.url,
                config=config,
                save_screenshot=screenshot,
                save_pdf=pdf,
                save_raw_html=include_raw_html,
            )
            if item.title and not capture_res.title:
                capture_res.title = item.title

            record = packager.add_source(
                source_id=source_id,
                input_url=item.url,
                capture_result=capture_res,
                selected=True,
                selection_note=note,
            )

            err_count = len(record.errors)
            if err_count > 0:
                console.print(f"[yellow]▲ [{source_id}] Captured with {err_count} warning(s)/error(s): {item.url}[/yellow]")
            else:
                console.print(f"[green]✔ [{source_id}] Captured successfully: {item.url}[/green]")

    # 5. Finalize bundle
    bundle_path = packager.finalize()

    # 6. Print Summary Report Table
    table = Table(title="Bundle Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Source ID", style="cyan", width=10)
    table.add_column("URL", style="dim", max_width=50, overflow="fold")
    table.add_column("Status", width=12)
    table.add_column("Artifacts", justify="right", width=10)
    table.add_column("Errors", justify="right", width=8)

    for rec in packager.sources:
        if not rec.selected:
            status = "[dim]Excluded[/dim]"
            art_count = "0"
        elif rec.errors:
            status = "[yellow]Warnings[/yellow]"
            art_count = str(len([k for k, v in rec.artifacts.model_dump().items() if v]))
        else:
            status = "[green]Success[/green]"
            art_count = str(len([k for k, v in rec.artifacts.model_dump().items() if v]))

        err_str = str(len(rec.errors)) if rec.errors else "0"
        table.add_row(rec.source_id, rec.input_url, status, art_count, err_str)

    console.print()
    console.print(table)
    console.print(f"\n[bold green]Bundle finalized at:[/bold green] [bold white]{bundle_path.resolve()}[/bold white]\n")

    return bundle_path


@app.command(name="urls")
def urls_command(
    urls: List[str] = typer.Argument(..., help="One or more URLs to capture and bundle."),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output directory path (defaults to auto-generated bundle ID).",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive/--no-interactive",
        "-i",
        help="Prompt to confirm each source before capturing.",
    ),
    screenshot: bool = typer.Option(
        True,
        "--screenshot/--no-screenshot",
        help="Capture full-page screenshot PNG.",
    ),
    pdf: bool = typer.Option(
        True,
        "--pdf/--no-pdf",
        help="Export rendered page as PDF.",
    ),
    include_raw_html: bool = typer.Option(
        False,
        "--include-raw-html",
        help="Capture raw HTTP response body and response headers.",
    ),
    include_links_table: bool = typer.Option(
        False,
        "--include-links-table",
        help="Append markdown table of extracted links to readable markdown.",
    ),
    redact_pattern: Optional[List[str]] = typer.Option(
        None,
        "--redact-pattern",
        help="Regex pattern(s) to redact from extracted markdown.",
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Page navigation and render timeout in seconds.",
    ),
):
    """Capture and bundle one or more URLs directly from command line arguments."""
    items = [SearchResultItem(url=u.strip()) for u in urls if u.strip()]
    _execute_bundling(
        items=items,
        out=out,
        interactive=interactive,
        screenshot=screenshot,
        pdf=pdf,
        include_raw_html=include_raw_html,
        include_links_table=include_links_table,
        redact_pattern=redact_pattern,
        timeout=timeout,
    )


@app.command(name="file")
def file_command(
    file_path: Path = typer.Argument(
        ...,
        help="Path to plain text file containing URLs (one per line).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output directory path (defaults to auto-generated bundle ID).",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive/--no-interactive",
        "-i",
        help="Prompt to confirm each source before capturing.",
    ),
    screenshot: bool = typer.Option(
        True,
        "--screenshot/--no-screenshot",
        help="Capture full-page screenshot PNG.",
    ),
    pdf: bool = typer.Option(
        True,
        "--pdf/--no-pdf",
        help="Export rendered page as PDF.",
    ),
    include_raw_html: bool = typer.Option(
        False,
        "--include-raw-html",
        help="Capture raw HTTP response body and response headers.",
    ),
    include_links_table: bool = typer.Option(
        False,
        "--include-links-table",
        help="Append markdown table of extracted links to readable markdown.",
    ),
    redact_pattern: Optional[List[str]] = typer.Option(
        None,
        "--redact-pattern",
        help="Regex pattern(s) to redact from extracted markdown.",
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Page navigation and render timeout in seconds.",
    ),
):
    """Capture and bundle URLs listed in a plain text file."""
    items = parse_url_file(file_path)
    _execute_bundling(
        items=items,
        out=out,
        interactive=interactive,
        screenshot=screenshot,
        pdf=pdf,
        include_raw_html=include_raw_html,
        include_links_table=include_links_table,
        redact_pattern=redact_pattern,
        timeout=timeout,
    )


@app.command(name="search-results")
def search_results_command(
    json_path: Path = typer.Argument(
        ...,
        help="Path to JSON file containing search results.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output directory path (defaults to auto-generated bundle ID).",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive/--no-interactive",
        "-i",
        help="Prompt to confirm each source before capturing.",
    ),
    screenshot: bool = typer.Option(
        True,
        "--screenshot/--no-screenshot",
        help="Capture full-page screenshot PNG.",
    ),
    pdf: bool = typer.Option(
        True,
        "--pdf/--no-pdf",
        help="Export rendered page as PDF.",
    ),
    include_raw_html: bool = typer.Option(
        False,
        "--include-raw-html",
        help="Capture raw HTTP response body and response headers.",
    ),
    include_links_table: bool = typer.Option(
        False,
        "--include-links-table",
        help="Append markdown table of extracted links to readable markdown.",
    ),
    redact_pattern: Optional[List[str]] = typer.Option(
        None,
        "--redact-pattern",
        help="Regex pattern(s) to redact from extracted markdown.",
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Page navigation and render timeout in seconds.",
    ),
):
    """Capture and bundle web sources from a search results JSON file."""
    items = parse_search_json(json_path)
    _execute_bundling(
        items=items,
        out=out,
        interactive=interactive,
        screenshot=screenshot,
        pdf=pdf,
        include_raw_html=include_raw_html,
        include_links_table=include_links_table,
        redact_pattern=redact_pattern,
        timeout=timeout,
    )


if __name__ == "__main__":
    app()
