from __future__ import annotations

from pathlib import Path
from typing import Callable

from .exceptions import JobCancelled
from .formatters import TranscriptResult, TranscriptSegment
from .paths import models_dir


def transcribe_audio(
    audio_file: Path,
    source_file: Path,
    model_name: str,
    language: str | None,
    device: str,
    compute_type: str,
    vad_filter: bool,
    task: str,
    should_cancel: Callable[[], bool] | None = None,
    on_segment: Callable[[int, float | None], None] | None = None,
) -> TranscriptResult:
    from faster_whisper import WhisperModel

    _raise_if_cancelled(should_cancel)
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(models_dir()),
    )
    _raise_if_cancelled(should_cancel)
    raw_segments, info = model.transcribe(
        str(audio_file),
        language=language,
        vad_filter=vad_filter,
        task=task,
    )
    duration = getattr(info, "duration", None)
    segments: list[TranscriptSegment] = []
    for index, segment in enumerate(raw_segments, start=1):
        _raise_if_cancelled(should_cancel)
        segments.append(
            TranscriptSegment(
                index=index,
                start=float(getattr(segment, "start")),
                end=float(getattr(segment, "end")),
                text=str(getattr(segment, "text")).strip(),
            )
        )
        if on_segment:
            on_segment(index, duration)
    _raise_if_cancelled(should_cancel)
    return TranscriptResult(
        source=str(source_file),
        language=getattr(info, "language", None),
        duration=duration,
        segments=segments,
    )


def _raise_if_cancelled(should_cancel: Callable[[], bool] | None) -> None:
    if should_cancel and should_cancel():
        raise JobCancelled("Cancelled while transcribing audio.")
