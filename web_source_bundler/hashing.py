"""SHA-256 hashing utilities for bytes, strings, files, and checksums file generation."""

import hashlib
from pathlib import Path
from typing import Dict, Union


def hash_bytes(data: bytes) -> str:
    """Calculate the SHA-256 hash of bytes and return in 'sha256:<hex>' format."""
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"


def hash_string(text: str) -> str:
    """Calculate the SHA-256 hash of a UTF-8 string and return in 'sha256:<hex>' format."""
    return hash_bytes(text.encode("utf-8"))


def hash_file(path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of a file using streaming reads.
    
    Returns hash in 'sha256:<hex>' format.
    """
    file_path = Path(path)
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def generate_checksums_content(file_hash_map: Dict[str, str]) -> str:
    """Generate the content of a standard checksums.sha256 file.
    
    Accepts a dictionary mapping file relative paths to hashes (either '<hex>' or 'sha256:<hex>').
    Converts paths to POSIX format, strips 'sha256:' prefixes, and formats as:
    <hex>  <posix_relpath>\n
    Entries are sorted deterministically by relative path.
    """
    lines = []
    # Sort deterministically by relative POSIX path
    for raw_path in sorted(file_hash_map.keys()):
        raw_hash = file_hash_map[raw_path]
        clean_hash = raw_hash.removeprefix("sha256:") if raw_hash.startswith("sha256:") else raw_hash
        # Normalize path separators to POSIX forward slash
        posix_path = str(raw_path).replace("\\", "/")
        lines.append(f"{clean_hash}  {posix_path}\n")

    return "".join(lines)
