from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


JobStatus = Literal["queued", "extracting", "transcribing", "writing", "completed", "failed", "cancelled"]


@dataclass
class JobRecord:
    id: str
    file_name: str
    input_path: str
    output_dir: str
    status: JobStatus
    model: str
    language: str | None
    device: str
    compute_type: str
    task: str
    vad_filter: bool
    keep_audio: bool
    created_at: str
    updated_at: str
    progress_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
