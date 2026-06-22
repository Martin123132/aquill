from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TranscriptSegment:
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptResult:
    source: str
    language: str | None
    duration: float | None
    segments: list[TranscriptSegment]

    @property
    def text(self) -> str:
        return "\n".join(segment.text.strip() for segment in self.segments if segment.text.strip())


def normalise_segments(raw_segments: Iterable[object]) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    for index, segment in enumerate(raw_segments, start=1):
        segments.append(
            TranscriptSegment(
                index=index,
                start=float(getattr(segment, "start")),
                end=float(getattr(segment, "end")),
                text=str(getattr(segment, "text")).strip(),
            )
        )
    return segments


def write_all_outputs(result: TranscriptResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_text(result, output_dir / "transcript.txt")
    write_json(result, output_dir / "transcript.json")
    write_srt(result.segments, output_dir / "subtitles.srt")
    write_vtt(result.segments, output_dir / "subtitles.vtt")


def write_text(result: TranscriptResult, path: Path) -> None:
    path.write_text(result.text + "\n", encoding="utf-8")


def write_json(result: TranscriptResult, path: Path) -> None:
    payload = {
        "source": result.source,
        "language": result.language,
        "duration": result.duration,
        "text": result.text,
        "segments": [asdict(segment) for segment in result.segments],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> TranscriptResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TranscriptResult(
        source=str(payload.get("source") or ""),
        language=payload.get("language"),
        duration=payload.get("duration"),
        segments=[
            TranscriptSegment(
                index=int(segment["index"]),
                start=float(segment["start"]),
                end=float(segment["end"]),
                text=str(segment["text"]),
            )
            for segment in payload.get("segments", [])
        ],
    )


def write_srt(segments: list[TranscriptSegment], path: Path) -> None:
    blocks = []
    for segment in segments:
        blocks.append(
            "\n".join(
                [
                    str(segment.index),
                    f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}",
                    segment.text,
                ]
            )
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_vtt(segments: list[TranscriptSegment], path: Path) -> None:
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.append(f"{format_vtt_time(segment.start)} --> {format_vtt_time(segment.end)}")
        blocks.append(segment.text)
        blocks.append("")
    path.write_text("\n".join(blocks), encoding="utf-8")


def format_srt_time(seconds: float) -> str:
    hours, minutes, secs, millis = split_time(seconds)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def format_vtt_time(seconds: float) -> str:
    hours, minutes, secs, millis = split_time(seconds)
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def split_time(seconds: float) -> tuple[int, int, int, int]:
    total_millis = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return hours, minutes, secs, millis
