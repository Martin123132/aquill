from __future__ import annotations

from datetime import datetime
from pathlib import Path


def make_job_name(input_file: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_stem = safe_name(input_file.stem) or "media"
    return f"{timestamp}-{safe_stem}"


def safe_name(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in value)
    return safe.strip("-")


def safe_file_name(value: str) -> str:
    path = Path(value).name
    suffix = Path(path).suffix.lower()
    stem = safe_name(Path(path).stem) or "media"
    safe_suffix = "".join(char for char in suffix if char.isalnum() or char == ".")
    return f"{stem}{safe_suffix}"
