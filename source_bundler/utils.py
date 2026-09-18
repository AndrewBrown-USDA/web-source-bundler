"""General utilities for path sanitization, timestamp formatting, and URL normalization."""

from datetime import datetime, timezone
import re
from typing import Optional
from urllib.parse import urlsplit, urlunsplit


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Convert an arbitrary string (e.g. URL or page title) into a safe filename slug.
    
    Ensures filename only contains alphanumeric characters, underscores, and hyphens.
    Prevents directory traversal and strips dangerous characters.
    """
    if not name:
        return "unnamed"

    # Normalize whitespace and replace slashes/colons/dots/special chars with hyphens
    cleaned = name.strip()
    # Replace path separators and query/param delimiters with dashes
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", cleaned)
    # Replace any non-alphanumeric (except hyphen and underscore) with hyphens
    cleaned = re.sub(r"[^\w\-]+", "-", cleaned)
    # Collapse multiple consecutive hyphens
    cleaned = re.sub(r"-+", "-", cleaned)
    # Collapse multiple consecutive underscores
    cleaned = re.sub(r"_+", "_", cleaned)
    # Strip leading and trailing hyphens/underscores/dots
    cleaned = cleaned.strip("-_.")

    if not cleaned:
        return "unnamed"

    # Enforce max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip("-_.")

    return cleaned or "unnamed"


def format_utc_timestamp(dt: Optional[datetime] = None) -> str:
    """Format a datetime object as an ISO 8601 UTC string: YYYY-MM-DDTHH:MM:SSZ.
    
    If dt is None, uses the current UTC time.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_bundle_id(dt: Optional[datetime] = None) -> str:
    """Generate a standard bundle identifier string: source-bundle-YYYYMMDDTHHMMSSZ."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    timestamp_str = dt.strftime("%Y%m%d%T%H%M%SZ").replace(":", "")
    # Equivalent to %Y%m%d%T%H%M%SZ without colons -> %Y%m%dT%H%M%SZ
    return f"source-bundle-{dt.strftime('%Y%m%dT%H%M%SZ')}"


def normalize_url(url: str) -> str:
    """Normalize a URL by trimming whitespace, lowercasing scheme/host, and normalizing trailing slashes."""
    if not url:
        return ""

    trimmed = url.strip()
    if not trimmed:
        return ""

    # Parse URL
    split = urlsplit(trimmed)
    scheme = split.scheme.lower()
    netloc = split.netloc.lower()
    path = split.path

    # Normalize default ports if present
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize trailing slash in path: remove trailing slash if path is longer than '/'
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Reassemble URL
    normalized = urlunsplit((scheme, netloc, path, split.query, split.fragment))
    return normalized
