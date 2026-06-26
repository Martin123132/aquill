from __future__ import annotations

import re

from .formatters import TranscriptResult, TranscriptSegment


SECTION_LABEL_RE = re.compile(r"^\[[^\]]+\]$")


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
