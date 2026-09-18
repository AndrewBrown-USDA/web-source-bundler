"""Core Pydantic models for web-source-bundler schemas and manifests."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 WebSourceBundler/0.1.0"
)


class ViewportConfig(BaseModel):
    """Viewport dimensions for browser rendering."""
    width: int = 1365
    height: int = 768


class CaptureConfig(BaseModel):
    """Deterministic browser capture configuration."""
    viewport: ViewportConfig = Field(default_factory=ViewportConfig)
    locale: str = "en-US"
    timezone: str = "UTC"
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: int = 30


class ToolInfo(BaseModel):
    """Tool metadata recording generator name and version."""
    name: str = "web-source-bundler"
    version: str = "0.1.0"


class SourceError(BaseModel):
    """Non-fatal error encountered during a capture or extraction stage."""
    stage: str
    message: str
    timestamp: datetime


class ArtifactRefs(BaseModel):
    """Relative POSIX paths to generated artifact files for a source."""
    rendered_html: Optional[str] = None
    readable_markdown: Optional[str] = None
    ast_json: Optional[str] = None
    screenshot: Optional[str] = None
    pdf: Optional[str] = None
    response_headers: Optional[str] = None
    raw_html: Optional[str] = None


SourceHashes = Dict[str, str]


class SourceRecord(BaseModel):
    """Full record and metadata for a single captured source."""
    source_id: str
    input_url: str
    final_url: Optional[str] = None
    title: Optional[str] = None
    selected: bool = True
    selection_note: Optional[str] = None
    fetched_at: Optional[datetime] = None
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    artifacts: ArtifactRefs = Field(default_factory=ArtifactRefs)
    hashes: Dict[str, str] = Field(default_factory=dict)
    errors: List[SourceError] = Field(default_factory=list)


class Manifest(BaseModel):
    """Top-level manifest describing a source bundle and all its contents."""
    bundle_id: str
    created_at: datetime
    tool: ToolInfo = Field(default_factory=ToolInfo)
    capture_config: CaptureConfig
    sources: List[SourceRecord] = Field(default_factory=list)


class ASTBlock(BaseModel):
    """Single structural content block in an extracted document."""
    type: str  # heading, paragraph, list, blockquote, code_block, table, link
    level: Optional[int] = None
    text: Optional[str] = None
    href: Optional[str] = None
    items: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ASTDocument(BaseModel):
    """Structured block-level representation of an extracted source document."""
    source_id: str
    title: Optional[str] = None
    final_url: Optional[str] = None
    blocks: List[ASTBlock] = Field(default_factory=list)


class SearchResultItem(BaseModel):
    """A search result item parsed from input JSON."""
    title: Optional[str] = None
    url: str
    snippet: Optional[str] = None
