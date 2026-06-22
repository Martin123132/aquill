from __future__ import annotations

import argparse
from pathlib import Path

from .naming import make_job_name
from .paths import configure_environment
from .pipeline import TranscriptionOptions, run_transcription_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="revenge-transcribe",
        description="Local-first transcription and subtitle generation.",
    )
    parser.add_argument("input", type=Path, help="Audio or video file to transcribe.")
    parser.add_argument("--out", type=Path, default=None, help="D-drive output directory.")
    parser.add_argument("--model", default="base", help="Whisper model name. Try tiny, base, small, medium, or large-v3.")
    parser.add_argument("--language", default=None, help="Optional source language code, such as en.")
    parser.add_argument("--device", default="auto", help="Device for faster-whisper: auto, cpu, or cuda.")
    parser.add_argument("--compute-type", default="int8", help="Compute type, such as int8, float16, or float32.")
    parser.add_argument("--task", choices=["transcribe", "translate"], default="transcribe")
    parser.add_argument("--keep-audio", action="store_true", help="Keep extracted WAV audio in the job folder.")
    parser.add_argument("--no-vad", action="store_true", help="Disable voice activity filtering.")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_environment()
    args = build_parser().parse_args(argv)
    input_file = args.input.expanduser().resolve()
    if not input_file.exists():
        raise SystemExit(f"Input file does not exist: {input_file}")
    if not input_file.is_file():
        raise SystemExit(f"Input path is not a file: {input_file}")

    print(f"Transcribing with model '{args.model}'")
    job_result = run_transcription_job(
        input_file=input_file,
        output_parent=args.out,
        options=TranscriptionOptions(
            model=args.model,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
            vad_filter=not args.no_vad,
            task=args.task,
            keep_audio=args.keep_audio,
        ),
        on_progress=lambda stage, message: print(f"Stage: {stage}" + (f" - {message}" if message else "")),
    )
    print(f"Done. Outputs written to {job_result.job_dir}")
    return 0
