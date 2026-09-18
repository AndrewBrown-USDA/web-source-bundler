"""Bundle packager for organizing, hashing, and writing source bundles."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from bs4 import BeautifulSoup

from source_bundler.extract import build_ast_document, extract_readable_html
from source_bundler.hashing import generate_checksums_content, hash_file
from source_bundler.markdown import (
    build_combined_markdown,
    build_readable_markdown,
    html_to_markdown,
)
from source_bundler.models import (
    ArtifactRefs,
    CaptureConfig,
    Manifest,
    SourceError,
    SourceRecord,
    ToolInfo,
)
from source_bundler.utils import format_utc_timestamp, generate_bundle_id


class BundlePackager:
    """Manages the creation and finalization of a source bundle directory."""

    def __init__(
        self,
        out_dir: Optional[Union[str, Path]] = None,
        config: Optional[CaptureConfig] = None,
        redact_patterns: Optional[List[str]] = None,
        include_links_table: bool = False,
        include_raw_html: bool = False,
    ) -> None:
        self.created_at: datetime = datetime.now(timezone.utc)
        self.bundle_id: str = generate_bundle_id(self.created_at)
        
        if out_dir is not None:
            self.out_dir: Path = Path(out_dir)
        else:
            self.out_dir = Path(self.bundle_id)

        self.config: CaptureConfig = config or CaptureConfig()
        self.redact_patterns: Optional[List[str]] = redact_patterns
        self.include_links_table: bool = include_links_table
        self.include_raw_html: bool = include_raw_html

        self.sources: List[SourceRecord] = []
        self.source_markdowns: Dict[str, str] = {}

        # Ensure base directories exist
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "sources").mkdir(parents=True, exist_ok=True)

    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safely get an attribute or dictionary key from capture result."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def add_source(
        self,
        source_id: str,
        input_url: str,
        capture_result: Any,
        selected: bool = True,
        selection_note: Optional[str] = None,
    ) -> SourceRecord:
        """Process capture result for a source and write its artifacts and metadata."""
        source_dir = self.out_dir / "sources" / source_id
        source_dir.mkdir(parents=True, exist_ok=True)

        final_url = self._get_val(capture_result, "final_url", input_url) or input_url
        title = self._get_val(capture_result, "title")
        http_status = self._get_val(capture_result, "http_status")
        content_type = self._get_val(capture_result, "content_type")
        rendered_html = self._get_val(capture_result, "rendered_html")
        raw_html = self._get_val(capture_result, "raw_html")
        screenshot_bytes = self._get_val(capture_result, "screenshot_bytes")
        pdf_bytes = self._get_val(capture_result, "pdf_bytes")
        response_headers = self._get_val(capture_result, "response_headers")
        raw_errors = self._get_val(capture_result, "errors", [])

        # Normalize errors into List[SourceError]
        errors: List[SourceError] = []
        for err in raw_errors or []:
            if isinstance(err, SourceError):
                errors.append(err)
            elif isinstance(err, dict):
                errors.append(SourceError(**err))
            else:
                errors.append(
                    SourceError(
                        stage="capture",
                        message=str(err),
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        artifacts = ArtifactRefs()
        hashes: Dict[str, str] = {}
        readable_md_content = ""

        # Process rendered content if available
        if rendered_html:
            rendered_path = source_dir / "rendered.html"
            rendered_path.write_text(rendered_html, encoding="utf-8")
            rel_rendered = f"sources/{source_id}/rendered.html"
            artifacts.rendered_html = rel_rendered
            hashes["rendered_html"] = hash_file(rendered_path)

            # Extraction and AST
            try:
                extracted_title, cleaned_html = extract_readable_html(rendered_html, url=final_url)
                if not title and extracted_title:
                    title = extracted_title

                ast_doc = build_ast_document(
                    source_id=source_id,
                    title=title or "",
                    final_url=final_url,
                    cleaned_html=cleaned_html,
                )
                ast_path = source_dir / "ast.json"
                ast_path.write_text(ast_doc.model_dump_json(indent=2), encoding="utf-8")
                rel_ast = f"sources/{source_id}/ast.json"
                artifacts.ast_json = rel_ast
                hashes["ast_json"] = hash_file(ast_path)

                # Markdown conversion
                content_md = html_to_markdown(cleaned_html)

                # Extracted links table
                extracted_links: Optional[List[Tuple[str, str]]] = None
                if self.include_links_table and cleaned_html:
                    extracted_links = []
                    soup = BeautifulSoup(cleaned_html, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag.get("href")
                        link_text = " ".join(a_tag.get_text().split()).strip() or href
                        if href:
                            extracted_links.append((link_text, href))

                fetched_at_str = format_utc_timestamp(datetime.now(timezone.utc))
                readable_md_content = build_readable_markdown(
                    source_id=source_id,
                    title=title or "",
                    input_url=input_url,
                    final_url=final_url,
                    fetched_at=fetched_at_str,
                    http_status=http_status,
                    content_md=content_md,
                    extracted_links=extracted_links,
                    include_links_table=self.include_links_table,
                    redact_patterns=self.redact_patterns,
                )
                readable_path = source_dir / "readable.md"
                readable_path.write_text(readable_md_content, encoding="utf-8")
                rel_readable = f"sources/{source_id}/readable.md"
                artifacts.readable_markdown = rel_readable
                hashes["readable_markdown"] = hash_file(readable_path)

            except Exception as exc:
                errors.append(
                    SourceError(
                        stage="extraction",
                        message=str(exc),
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        # Process optional raw HTML and headers
        if self.include_raw_html:
            if raw_html:
                raw_html_path = source_dir / "raw.html"
                raw_html_path.write_text(raw_html, encoding="utf-8")
                rel_raw_html = f"sources/{source_id}/raw.html"
                artifacts.raw_html = rel_raw_html
                hashes["raw_html"] = hash_file(raw_html_path)

            if response_headers:
                headers_path = source_dir / "response_headers.json"
                headers_path.write_text(json.dumps(response_headers, indent=2), encoding="utf-8")
                rel_headers = f"sources/{source_id}/response_headers.json"
                artifacts.response_headers = rel_headers
                hashes["response_headers"] = hash_file(headers_path)

        # Process binary artifacts
        if screenshot_bytes:
            screenshot_path = source_dir / "screenshot.png"
            screenshot_path.write_bytes(screenshot_bytes)
            rel_screenshot = f"sources/{source_id}/screenshot.png"
            artifacts.screenshot = rel_screenshot
            hashes["screenshot"] = hash_file(screenshot_path)

        if pdf_bytes:
            pdf_path = source_dir / "page.pdf"
            pdf_path.write_bytes(pdf_bytes)
            rel_pdf = f"sources/{source_id}/page.pdf"
            artifacts.pdf = rel_pdf
            hashes["pdf"] = hash_file(pdf_path)

        # Build SourceRecord
        record = SourceRecord(
            source_id=source_id,
            input_url=input_url,
            final_url=final_url,
            title=title,
            selected=selected,
            selection_note=selection_note,
            fetched_at=datetime.now(timezone.utc),
            http_status=http_status,
            content_type=content_type,
            artifacts=artifacts,
            hashes=hashes,
            errors=errors,
        )

        # Write metadata.json
        metadata_path = source_dir / "metadata.json"
        metadata_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

        # Save markdown and record internally
        self.source_markdowns[source_id] = readable_md_content
        self.sources.append(record)
        return record

    def finalize(self) -> Path:
        """Finalize the bundle by writing manifest.json, combined.md, and checksums.sha256."""
        # 1. Manifest
        manifest = Manifest(
            bundle_id=self.bundle_id,
            created_at=self.created_at,
            tool=ToolInfo(),
            capture_config=self.config,
            sources=self.sources,
        )
        manifest_path = self.out_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        # 2. Combined markdown
        combined_md_content = build_combined_markdown(manifest, self.source_markdowns)
        combined_path = self.out_dir / "combined.md"
        combined_path.write_text(combined_md_content, encoding="utf-8")

        # 3. Checksums for all bundle files (excluding checksums.sha256 itself)
        file_hash_map: Dict[str, str] = {}
        for file_path in sorted(self.out_dir.rglob("*")):
            if file_path.is_file() and file_path.name != "checksums.sha256":
                rel_posix = file_path.relative_to(self.out_dir).as_posix()
                file_hash_map[rel_posix] = hash_file(file_path)

        checksums_content = generate_checksums_content(file_hash_map)
        checksums_path = self.out_dir / "checksums.sha256"
        checksums_path.write_text(checksums_content, encoding="utf-8")

        return self.out_dir
