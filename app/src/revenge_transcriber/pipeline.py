from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .exceptions import JobCancelled
from .formatters import TranscriptResult, write_all_outputs
from .media import extract_audio
from .naming import make_job_name
from .paths import require_output_dir, tmp_dir
from .transcriber import transcribe_audio


ProgressCallback = Callable[[str, str | None], None]
CancellationCheck = Callable[[], bool]


@dataclass(frozen=True)
class TranscriptionOptions:
    model: str = "base"
    language: str | None = None
    device: str = "auto"
    compute_type: str = "int8"
    task: str = "transcribe"
    vad_filter: bool = True
    keep_audio: bool = False


@dataclass(frozen=True)
class TranscriptionJobResult:
    job_dir: Path
    result: TranscriptResult


def run_transcription_job(
    input_file: Path,
    output_parent: Path | None,
    options: TranscriptionOptions,
    job_name: str | None = None,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancellationCheck | None = None,
) -> TranscriptionJobResult:
    input_file = input_file.expanduser().resolve()
    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")
    if not input_file.is_file():
        raise ValueError(f"Input path is not a file: {input_file}")

    output_dir = require_output_dir(output_parent)
    job_dir = output_dir / (job_name or make_job_name(input_file))
    job_dir.mkdir(parents=True, exist_ok=True)

    working_audio = tmp_dir() / f"{job_dir.name}.wav"
    audio_moved = False
    try:
        _raise_if_cancelled(should_cancel)
        _progress(on_progress, "extracting", "Extracting audio with FFmpeg.")
        extract_audio(input_file, working_audio, should_cancel=should_cancel)

        _raise_if_cancelled(should_cancel)
        _progress(on_progress, "transcribing", "Loading Whisper and transcribing audio.")
        result = transcribe_audio(
            audio_file=working_audio,
            source_file=input_file,
            model_name=options.model,
            language=options.language,
            device=options.device,
            compute_type=options.compute_type,
            vad_filter=options.vad_filter,
            task=options.task,
            should_cancel=should_cancel,
            on_segment=lambda count, duration: _progress(
                on_progress,
                "transcribing",
                segment_message(count, duration),
            ),
        )

        _raise_if_cancelled(should_cancel)
        _progress(on_progress, "writing", "Writing transcript and subtitle exports.")
        write_all_outputs(result, job_dir)
        if options.keep_audio:
            shutil.move(str(working_audio), str(job_dir / "audio.wav"))
            audio_moved = True
        else:
            working_audio.unlink(missing_ok=True)

        _progress(on_progress, "completed", "Completed.")
        return TranscriptionJobResult(job_dir=job_dir, result=result)
    finally:
        if not audio_moved:
            working_audio.unlink(missing_ok=True)


def _progress(callback: ProgressCallback | None, stage: str, message: str | None = None) -> None:
    if callback:
        callback(stage, message)


def _raise_if_cancelled(should_cancel: CancellationCheck | None) -> None:
    if should_cancel and should_cancel():
        raise JobCancelled("Cancelled before the next transcription stage.")


def segment_message(count: int, duration: float | None) -> str:
    if duration:
        return f"Transcribed {count} segment{'s' if count != 1 else ''} from {format_duration(duration)}."
    return f"Transcribed {count} segment{'s' if count != 1 else ''}."


def format_duration(seconds: float) -> str:
    rounded = max(0, round(seconds))
    minutes, rest = divmod(rounded, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{rest:02}"
    return f"{minutes}:{rest:02}"
