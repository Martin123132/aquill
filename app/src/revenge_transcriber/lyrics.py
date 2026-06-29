from __future__ import annotations

import re
import shutil
from pathlib import Path

from .formatters import TranscriptResult, TranscriptSegment


SECTION_LABEL_RE = re.compile(r"^\[[^\]]+\]$")
ARTIFACT_BACKUPS = {
    "transcript.txt": "transcript.original.txt",
    "transcript.json": "transcript.original.json",
    "subtitles.srt": "subtitles.original.srt",
    "subtitles.vtt": "subtitles.original.vtt",
}


class LyricsAlignmentError(ValueError):
    """Raised when supplied lyrics cannot be converted into timed lines."""


def lyric_lines_from_text(lyrics: str) -> list[str]:
    lines: list[str] = []
    for raw_line in lyrics.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        if line.lower() == "lyrics:":
            continue
        if SECTION_LABEL_RE.fullmatch(line):
            continue
        lines.append(line)

    if not lines:
        raise LyricsAlignmentError("Paste at least one lyric line.")
    return lines


def align_lyrics_to_transcript(base: TranscriptResult, lyrics: str) -> TranscriptResult:
    lines = lyric_lines_from_text(lyrics)
    duration = transcript_duration(base)

    if base.segments and len(lines) <= len(base.segments):
        segments = align_to_existing_segments(base.segments, lines)
    else:
        segments = distribute_evenly(lines, duration)

    return TranscriptResult(
        source=base.source,
        language=base.language,
        duration=duration,
        segments=segments,
    )


def transcript_duration(transcript: TranscriptResult) -> float:
    if transcript.duration and transcript.duration > 0:
        return float(transcript.duration)
    if transcript.segments:
        return max(segment.end for segment in transcript.segments)
    return 0.0


def align_to_existing_segments(base_segments: list[TranscriptSegment], lines: list[str]) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    total_segments = len(base_segments)
    total_lines = len(lines)

    for line_index, line in enumerate(lines):
        start_index = int(line_index * total_segments / total_lines)
        end_index = int((line_index + 1) * total_segments / total_lines)
        if end_index <= start_index:
            end_index = start_index + 1
        grouped = base_segments[start_index:end_index]
        start = grouped[0].start
        end = grouped[-1].end
        if end <= start:
            end = start + 0.5
        segments.append(TranscriptSegment(index=line_index + 1, start=start, end=end, text=line))

    return segments


def distribute_evenly(lines: list[str], duration: float) -> list[TranscriptSegment]:
    if duration <= 0:
        duration = len(lines) * 3.0
    duration = max(duration, len(lines) * 0.5)
    step = duration / len(lines)
    return [
        TranscriptSegment(
            index=index + 1,
            start=index * step,
            end=(index + 1) * step,
            text=line,
        )
        for index, line in enumerate(lines)
    ]


def backup_original_outputs(output_dir: Path) -> list[str]:
    output_dir = output_dir.resolve()
    backed_up: list[str] = []
    for source_name, backup_name in ARTIFACT_BACKUPS.items():
        source = output_dir / source_name
        backup = output_dir / backup_name
        if source.exists() and source.is_file() and not backup.exists():
            shutil.copy2(source, backup)
            backed_up.append(backup_name)
    return backed_up


def original_outputs_available(output_dir: Path) -> bool:
    return (output_dir / ARTIFACT_BACKUPS["transcript.json"]).exists()


def restore_original_outputs(output_dir: Path) -> list[str]:
    output_dir = output_dir.resolve()
    if not original_outputs_available(output_dir):
        raise LyricsAlignmentError("Original transcript backup is not available.")

    restored: list[str] = []
    for source_name, backup_name in ARTIFACT_BACKUPS.items():
        backup = output_dir / backup_name
        if backup.exists() and backup.is_file():
            shutil.copy2(backup, output_dir / source_name)
            restored.append(source_name)
    return restored
