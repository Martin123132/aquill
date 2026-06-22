from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from .exceptions import JobCancelled


class FFmpegError(RuntimeError):
    """Raised when FFmpeg cannot extract audio."""


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise FFmpegError(
            "FFmpeg was not found on PATH and imageio-ffmpeg is not installed."
        ) from exc

    bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if not bundled_ffmpeg:
        raise FFmpegError("Could not locate a bundled FFmpeg executable.")
    return bundled_ffmpeg


def extract_audio(
    input_file: Path,
    output_file: Path,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    ffmpeg = require_ffmpeg()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_file),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_file),
    ]
    process = subprocess.Popen(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    while process.poll() is None:
        if should_cancel and should_cancel():
            process.terminate()
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            output_file.unlink(missing_ok=True)
            raise JobCancelled("Cancelled while extracting audio.")
        time.sleep(0.2)

    stdout, stderr = process.communicate()
    if process.returncode != 0:
        detail = stderr.strip() or stdout.strip() or "Unknown FFmpeg error"
        raise FFmpegError(detail)
    return output_file
