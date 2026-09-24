"""
FIN Storage Safety Utilities.
Provides concurrency-safe atomic file writes, snapshot ID path traversal validation,
and deterministic JSON persistence for snapshot activations and rollbacks.
"""

import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Dict, Optional

# Alphanumeric snapshot ID pattern (no directory separators or traversal)
SNAPSHOT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")

# Process-level concurrency lock for snapshot mutations
_SNAPSHOT_LOCK = threading.Lock()


class StorageSecurityError(ValueError):
    """Raised when an unsafe path or invalid snapshot identifier is encountered."""
    pass


def validate_snapshot_id(snapshot_id: str) -> str:
    """
    Validates snapshot ID against path traversal sequences and suspicious characters.
    Raises StorageSecurityError if invalid.
    """
    if not snapshot_id or not isinstance(snapshot_id, str):
        raise StorageSecurityError("Snapshot ID must be a non-empty string.")

    clean = snapshot_id.strip()
    if not SNAPSHOT_ID_PATTERN.match(clean):
        raise StorageSecurityError(
            f"Invalid snapshot ID: '{snapshot_id}'. Must be alphanumeric with underscores/hyphens, length 1-64."
        )

    if ".." in clean or "/" in clean or "\\" in clean or "\x00" in clean:
        raise StorageSecurityError(f"Directory traversal detected in snapshot ID: '{snapshot_id}'")

    return clean


def safe_atomic_write_json(
    target_path: Path | str,
    data: Dict[str, Any],
    indent: int = 2,
    base_dir: Optional[Path | str] = None,
) -> None:
    """
    Safely writes JSON data to target_path using an atomic tempfile-and-replace strategy.
    Ensures readers never observe partial writes or file corruption during unexpected crashes.
    """
    target = Path(target_path).resolve()

    if base_dir:
        base = Path(base_dir).resolve()
        if not str(target).startswith(str(base)):
            raise StorageSecurityError(
                f"Path traversal security violation: '{target}' escapes allowed base directory '{base}'"
            )

    target.parent.mkdir(parents=True, exist_ok=True)

    # Serialize JSON with deterministic sorting
    json_bytes = json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False).encode("utf-8")

    # Write to a temporary file in the same directory to ensure atomic os.replace across filesystem boundaries
    temp_file = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=str(target.parent),
        prefix=".tmp_atomic_",
        delete=False,
    )
    try:
        temp_file.write(json_bytes)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()

        # Atomic replacement
        os.replace(temp_file.name, str(target))
    except Exception as exc:
        if os.path.exists(temp_file.name):
            try:
                os.remove(temp_file.name)
            except OSError:
                pass
        raise exc


def safe_atomic_write_bytes(
    target_path: Path | str,
    content: bytes,
    base_dir: Optional[Path | str] = None,
) -> None:
    """
    Safely writes binary content to target_path atomically.
    """
    target = Path(target_path).resolve()

    if base_dir:
        base = Path(base_dir).resolve()
        if not str(target).startswith(str(base)):
            raise StorageSecurityError(
                f"Path traversal security violation: '{target}' escapes allowed base directory '{base}'"
            )

    target.parent.mkdir(parents=True, exist_ok=True)

    temp_file = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=str(target.parent),
        prefix=".tmp_atomic_bytes_",
        delete=False,
    )
    try:
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()

        os.replace(temp_file.name, str(target))
    except Exception as exc:
        if os.path.exists(temp_file.name):
            try:
                os.remove(temp_file.name)
            except OSError:
                pass
        raise exc


def get_snapshot_lock() -> threading.Lock:
    """Returns the process-wide lock for atomic snapshot mutations."""
    return _SNAPSHOT_LOCK
