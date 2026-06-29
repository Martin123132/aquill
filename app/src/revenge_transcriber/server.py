from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .archive import ArchiveImportError, build_job_archive, import_job_archive, preview_job_archive
from .db import delete_job as db_delete_job
from .db import get_job as db_get_job
from .db import initialise_database, insert_job, list_jobs as db_list_jobs
from .db import list_output_dirs, update_job_status
from .formatters import TranscriptResult, TranscriptSegment, read_json, write_all_outputs
from .lyrics import (
    LyricsAlignmentError,
    align_lyrics_to_transcript,
    backup_original_outputs,
    original_outputs_available,
    restore_original_outputs,
)
from .naming import make_job_name, safe_file_name
from .paths import cache_dir, configure_environment, data_dir, inputs_dir, models_dir, outputs_dir, project_root, tmp_dir
from .pipeline import TranscriptionOptions, run_transcription_job
from .records import JobRecord, JobStatus

configure_environment()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .exceptions import JobCancelled


app = FastAPI(title="Aquill API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5190",
        "http://127.0.0.1:5190",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="transcribe")
_model_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="model")
_futures: dict[str, Future[None]] = {}
_cancel_events: dict[str, threading.Event] = {}
_futures_lock = threading.Lock()
_model_status: dict[str, dict[str, str | None]] = {}
_model_status_lock = threading.Lock()

ARTIFACTS = {
    "txt": "transcript.txt",
    "json": "transcript.json",
    "srt": "subtitles.srt",
    "vtt": "subtitles.vtt",
    "audio": "audio.wav",
}

ACTIVE_STATUSES = {"queued", "extracting", "transcribing", "writing"}
RUNNING_STATUSES = {"extracting", "transcribing", "writing"}
FINAL_STATUSES = {"completed", "failed", "cancelled"}
STAGE_MESSAGES = {
    "queued": "Waiting for the transcription worker.",
    "extracting": "Extracting audio with FFmpeg.",
    "transcribing": "Loading Whisper and transcribing audio.",
    "writing": "Writing transcript and subtitle exports.",
    "completed": "Completed.",
    "failed": "Failed.",
    "cancelled": "Cancelled.",
}
MODELS = ["tiny", "base", "small", "medium", "large-v3"]
MODEL_DESCRIPTIONS = {
    "tiny": "Fastest first-pass checks",
    "base": "Good default for quick local jobs",
    "small": "Better accuracy without feeling huge",
    "medium": "Higher accuracy, slower CPU work",
    "large-v3": "Best accuracy, largest download",
}

initialise_database()


@app.get("/api/health")
def health() -> dict[str, object]:
    jobs = db_list_jobs()
    return {
        "status": "ok",
        "root": str(project_root()),
        "database_path": str(data_dir() / "transcriber.db"),
        "database_available": (data_dir() / "transcriber.db").exists(),
        "worker_busy": any(job_future_running(job.id) for job in jobs),
        "active_jobs": sum(1 for job in jobs if job.status in ACTIVE_STATUSES),
        "total_jobs": len(jobs),
    }


@app.get("/api/jobs")
def list_jobs() -> dict[str, list[dict[str, object]]]:
    return {"jobs": [public_job(job) for job in db_list_jobs()]}


@app.post("/api/jobs", status_code=202)
async def create_job(
    file: UploadFile = File(...),
    model: str = Form("base"),
    language: str | None = Form(None),
    device: str = Form("auto"),
    compute_type: str = Form("int8"),
    task: Literal["transcribe", "translate"] = Form("transcribe"),
    vad_filter: bool = Form(True),
    keep_audio: bool = Form(False),
) -> dict[str, object]:
    job_id = uuid.uuid4().hex
    source_name = safe_file_name(file.filename or "media")
    input_path = inputs_dir() / f"{job_id}-{source_name}"
    output_dir = outputs_dir() / make_job_name(Path(source_name))

    await save_upload(file, input_path)
    now = timestamp()
    job = JobRecord(
        id=job_id,
        file_name=file.filename or source_name,
        input_path=str(input_path),
        output_dir=str(output_dir),
        status="queued",
        model=model,
        language=normalise_language(language),
        device=device,
        compute_type=compute_type,
        task=task,
        vad_filter=vad_filter,
        keep_audio=keep_audio,
        created_at=now,
        updated_at=now,
        progress_message=STAGE_MESSAGES["queued"],
    )
    insert_job(job)

    options = TranscriptionOptions(
        model=model,
        language=job.language,
        device=device,
        compute_type=compute_type,
        task=task,
        vad_filter=vad_filter,
        keep_audio=keep_audio,
    )
    submit_job(job_id, input_path, output_dir, options)
    return {"job": public_job(job)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    return {"job": public_job(require_job(job_id))}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, object]:
    job = require_job(job_id)
    if job.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail=f"Job is {job.status}.")

    with _futures_lock:
        future = _futures.get(job_id)
        cancel_event = _cancel_events.get(job_id)
        if cancel_event:
            cancel_event.set()

        cancelled_before_start = future.cancel() if future is not None else False
        if cancelled_before_start:
            _futures.pop(job_id, None)
            _cancel_events.pop(job_id, None)

    message = (
        "Cancelled before transcription started."
        if cancelled_before_start or job.status == "queued"
        else "Cancellation requested; stopping at the next safe checkpoint."
    )
    update_job(job_id, "cancelled", progress_message=message)
    return {"job": public_job(require_job(job_id))}


@app.post("/api/jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: str) -> dict[str, object]:
    original = require_job(job_id)
    input_path = Path(original.input_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Original input file is not available.")

    new_id = uuid.uuid4().hex
    now = timestamp()
    output_dir = outputs_dir() / make_job_name(Path(original.file_name))
    job = JobRecord(
        id=new_id,
        file_name=original.file_name,
        input_path=original.input_path,
        output_dir=str(output_dir),
        status="queued",
        model=original.model,
        language=original.language,
        device=original.device,
        compute_type=original.compute_type,
        task=original.task,
        vad_filter=original.vad_filter,
        keep_audio=original.keep_audio,
        created_at=now,
        updated_at=now,
        progress_message=STAGE_MESSAGES["queued"],
    )
    insert_job(job)
    submit_job(new_id, input_path, output_dir, options_from_job(job))
    return {"job": public_job(job)}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, delete_files: bool = True) -> dict[str, object]:
    job = require_job(job_id)
    with _futures_lock:
        future = _futures.get(job_id)

    if job.status in RUNNING_STATUSES or (future is not None and future.running()):
        raise HTTPException(status_code=409, detail="Running jobs cannot be deleted.")

    with _futures_lock:
        future = _futures.pop(job_id, None)
        _cancel_events.pop(job_id, None)
    if future is not None:
        future.cancel()

    if delete_files:
        remove_job_files(job)
    db_delete_job(job_id)
    return {"deleted": True, "id": job_id}


@app.post("/api/jobs/{job_id}/open-output")
def open_output_folder(job_id: str) -> dict[str, str]:
    job = require_job(job_id)
    output_dir = Path(job.output_dir)
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output folder is not available.")
    os.startfile(str(output_dir))  # type: ignore[attr-defined]
    return {"opened": str(output_dir)}


@app.get("/api/jobs/{job_id}/transcript")
def get_transcript(job_id: str) -> JSONResponse:
    job = require_completed_job(job_id)
    path = Path(job.output_dir) / "transcript.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Transcript JSON is not available.")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


class SegmentUpdate(BaseModel):
    index: int = Field(ge=1)
    text: str


class TranscriptUpdate(BaseModel):
    segments: list[SegmentUpdate]


class LyricsAlignmentRequest(BaseModel):
    lyrics: str = Field(min_length=1)


@app.put("/api/jobs/{job_id}/transcript")
def update_transcript(job_id: str, update: TranscriptUpdate) -> JSONResponse:
    job = require_completed_job(job_id)
    output_dir = Path(job.output_dir)
    transcript_path = output_dir / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript JSON is not available.")

    current = read_json(transcript_path)
    edits = {segment.index: segment.text.strip() for segment in update.segments}
    existing_indexes = {segment.index for segment in current.segments}
    unknown_indexes = sorted(set(edits) - existing_indexes)
    if unknown_indexes:
        raise HTTPException(status_code=400, detail=f"Unknown segment index: {unknown_indexes[0]}")

    edited = TranscriptResult(
        source=current.source,
        language=current.language,
        duration=current.duration,
        segments=[
            TranscriptSegment(
                index=segment.index,
                start=segment.start,
                end=segment.end,
                text=edits.get(segment.index, segment.text).strip(),
            )
            for segment in current.segments
        ],
    )
    write_all_outputs(edited, output_dir)
    update_job_status(
        job.id,
        "completed",
        timestamp(),
        error=None,
        progress_message="Transcript edits saved and exports regenerated.",
    )
    return JSONResponse(json.loads(transcript_path.read_text(encoding="utf-8")))


@app.post("/api/jobs/{job_id}/lyrics/preview")
def preview_job_lyrics(job_id: str, request: LyricsAlignmentRequest) -> dict[str, object]:
    job = require_completed_job(job_id)
    output_dir = Path(job.output_dir)
    transcript_path = output_dir / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript JSON is not available.")

    current = read_json(transcript_path)
    try:
        aligned = align_lyrics_to_transcript(current, request.lyrics)
    except LyricsAlignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "line_count": len(aligned.segments),
        "transcript": transcript_payload(aligned),
        "has_original_transcript": original_outputs_available(output_dir),
    }


@app.post("/api/jobs/{job_id}/lyrics")
def align_job_lyrics(job_id: str, request: LyricsAlignmentRequest) -> dict[str, object]:
    job = require_completed_job(job_id)
    output_dir = Path(job.output_dir)
    transcript_path = output_dir / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript JSON is not available.")

    current = read_json(transcript_path)
    try:
        aligned = align_lyrics_to_transcript(current, request.lyrics)
    except LyricsAlignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    backup_original_outputs(output_dir)
    write_all_outputs(aligned, output_dir)
    line_count = len(aligned.segments)
    update_job_status(
        job.id,
        "completed",
        timestamp(),
        error=None,
        progress_message=f"Lyrics aligned into {line_count} timed line{'s' if line_count != 1 else ''}.",
    )
    return {
        "line_count": line_count,
        "transcript": transcript_payload(aligned),
        "has_original_transcript": original_outputs_available(output_dir),
    }


@app.post("/api/jobs/{job_id}/transcript/restore-original")
def restore_original_transcript(job_id: str) -> dict[str, object]:
    job = require_completed_job(job_id)
    output_dir = Path(job.output_dir)
    transcript_path = output_dir / "transcript.json"
    try:
        restored = restore_original_outputs(output_dir)
    except LyricsAlignmentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript JSON is not available.")

    update_job_status(
        job.id,
        "completed",
        timestamp(),
        error=None,
        progress_message=f"Original transcript restored ({len(restored)} artifacts).",
    )
    return {
        "restored_artifacts": restored,
        "transcript": json.loads(transcript_path.read_text(encoding="utf-8")),
        "has_original_transcript": original_outputs_available(output_dir),
    }


@app.get("/api/jobs/{job_id}/download/{artifact}")
def download_artifact(job_id: str, artifact: str) -> FileResponse:
    job = require_completed_job(job_id)
    file_name = ARTIFACTS.get(artifact)
    if file_name is None:
        raise HTTPException(status_code=404, detail="Unknown artifact.")

    path = Path(job.output_dir) / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{file_name} is not available.")
    return FileResponse(path, filename=file_name)


@app.get("/api/jobs/{job_id}/archive")
def download_job_archive(job_id: str) -> FileResponse:
    job = require_completed_job(job_id)
    archive_path = build_job_archive(job)
    file_name = f"{safe_file_name(Path(job.file_name).stem or job.id)}-{job.id[:8]}-archive.zip"
    return FileResponse(
        archive_path,
        filename=file_name,
        media_type="application/zip",
        background=BackgroundTask(lambda: archive_path.unlink(missing_ok=True)),
    )


@app.post("/api/jobs/import", status_code=201)
async def import_archive(file: UploadFile = File(...)) -> dict[str, object]:
    archive_name = safe_file_name(file.filename or "archive.zip")
    upload_path = inputs_dir() / f"import-{uuid.uuid4().hex}-{archive_name}"
    try:
        await save_upload(file, upload_path)
        job = import_job_archive(upload_path, timestamp())
        insert_job(job)
        return {"job": public_job(job)}
    except ArchiveImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        upload_path.unlink(missing_ok=True)


@app.post("/api/jobs/import/preview")
async def preview_archive_import(file: UploadFile = File(...)) -> dict[str, object]:
    archive_name = safe_file_name(file.filename or "archive.zip")
    upload_path = inputs_dir() / f"preview-{uuid.uuid4().hex}-{archive_name}"
    try:
        await save_upload(file, upload_path)
        return {"preview": preview_job_archive(upload_path)}
    except ArchiveImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        upload_path.unlink(missing_ok=True)


@app.get("/api/models")
def list_models() -> dict[str, object]:
    return {
        "models_dir": str(models_dir()),
        "models": [model_payload(model) for model in MODELS],
    }


@app.get("/api/system/storage")
def storage_status() -> dict[str, str]:
    return {
        "project_root": str(project_root()),
        "inputs_dir": str(inputs_dir()),
        "outputs_dir": str(outputs_dir()),
        "models_dir": str(models_dir()),
        "data_dir": str(data_dir()),
        "tmp_dir": str(tmp_dir()),
        "cache_dir": str(cache_dir()),
    }


@app.post("/api/models/{model}/download", status_code=202)
def download_model(model: str) -> dict[str, object]:
    model = require_model(model)
    with _model_status_lock:
        status = _model_status.get(model, {}).get("status")
        if status == "downloading":
            return {"model": model_payload(model)}
        _model_status[model] = {"status": "downloading", "error": None}
    _model_executor.submit(download_model_job, model)
    return {"model": model_payload(model)}


@app.delete("/api/models/{model}")
def remove_model(model: str) -> dict[str, object]:
    model = require_model(model)
    with _model_status_lock:
        if _model_status.get(model, {}).get("status") == "downloading":
            raise HTTPException(status_code=409, detail="Model is downloading.")

    path = model_path(model)
    if path.exists():
        shutil.rmtree(path)
    return {"model": model_payload(model)}


async def save_upload(file: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)
    await file.close()


def submit_job(job_id: str, input_path: Path, output_dir: Path, options: TranscriptionOptions) -> None:
    cancel_event = threading.Event()
    future = _executor.submit(process_job, job_id, input_path, output_dir, options, cancel_event)
    with _futures_lock:
        _futures[job_id] = future
        _cancel_events[job_id] = cancel_event
        if future.done():
            _futures.pop(job_id, None)
            _cancel_events.pop(job_id, None)


def process_job(
    job_id: str,
    input_path: Path,
    output_dir: Path,
    options: TranscriptionOptions,
    cancel_event: threading.Event,
) -> None:
    try:
        job = require_job(job_id)
        if cancel_event.is_set() or job.status == "cancelled":
            update_job(job_id, status="cancelled", progress_message="Cancelled before transcription started.")
            return
        run_transcription_job(
            input_file=input_path,
            output_parent=output_dir.parent,
            options=options,
            job_name=output_dir.name,
            on_progress=lambda stage, message: update_job(job_id, status=stage, progress_message=message),
            should_cancel=cancel_event.is_set,
        )
    except JobCancelled as exc:
        update_job(job_id, status="cancelled", progress_message=str(exc) or STAGE_MESSAGES["cancelled"])
    except Exception as exc:  # noqa: BLE001 - local job runner should surface any failure.
        update_job(job_id, status="failed", error=str(exc), progress_message=str(exc))
    finally:
        with _futures_lock:
            _futures.pop(job_id, None)
            _cancel_events.pop(job_id, None)


def update_job(
    job_id: str,
    status: JobStatus,
    error: str | None = None,
    progress_message: str | None = None,
) -> None:
    current = db_get_job(job_id)
    if current and current.status in FINAL_STATUSES and status not in FINAL_STATUSES:
        return

    now = timestamp()
    kwargs: dict[str, object | None] = {
        "error": error if status == "failed" else None,
        "progress_message": progress_message or STAGE_MESSAGES[status],
    }
    if current and current.started_at is None and status in RUNNING_STATUSES:
        kwargs["started_at"] = now
    if status in FINAL_STATUSES:
        kwargs["completed_at"] = now
    update_job_status(job_id, status, now, **kwargs)


def require_job(job_id: str) -> JobRecord:
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def require_completed_job(job_id: str) -> JobRecord:
    job = require_job(job_id)
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}.")
    return job


def options_from_job(job: JobRecord) -> TranscriptionOptions:
    return TranscriptionOptions(
        model=job.model,
        language=job.language,
        device=job.device,
        compute_type=job.compute_type,
        task=job.task,
        vad_filter=job.vad_filter,
        keep_audio=job.keep_audio,
    )


def public_job(job: JobRecord) -> dict[str, object]:
    payload = asdict(job)
    if job.status == "completed":
        payload["artifacts"] = {
            key: f"/api/jobs/{job.id}/download/{key}"
            for key, file_name in ARTIFACTS.items()
            if (Path(job.output_dir) / file_name).exists()
        }
        payload["transcript_url"] = f"/api/jobs/{job.id}/transcript"
        payload["archive_url"] = f"/api/jobs/{job.id}/archive"
    else:
        payload["artifacts"] = {}
        payload["transcript_url"] = None
        payload["archive_url"] = None
    payload["has_original_transcript"] = job.status == "completed" and original_outputs_available(Path(job.output_dir))
    payload["can_cancel"] = job.status in ACTIVE_STATUSES
    payload["can_retry"] = job.status in {"completed", "failed", "cancelled"}
    payload["can_delete"] = job.status not in RUNNING_STATUSES and not job_future_running(job.id)
    payload["can_open_output"] = Path(job.output_dir).exists()
    return payload


def job_future_running(job_id: str) -> bool:
    with _futures_lock:
        future = _futures.get(job_id)
    return future.running() if future is not None else False


def normalise_language(language: str | None) -> str | None:
    if language is None:
        return None
    language = language.strip()
    return language or None


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def transcript_payload(result: TranscriptResult) -> dict[str, object]:
    return {
        "source": result.source,
        "language": result.language,
        "duration": result.duration,
        "text": result.text,
        "segments": [asdict(segment) for segment in result.segments],
    }


def remove_job_files(job: JobRecord) -> None:
    output_dir = Path(job.output_dir).resolve()
    input_path = Path(job.input_path).resolve()
    root_outputs = outputs_dir().resolve()
    root_inputs = inputs_dir().resolve()
    if output_dir.exists() and output_dir.is_relative_to(root_outputs):
        shutil.rmtree(output_dir)
    if input_path.exists() and input_path.is_file() and input_path.is_relative_to(root_inputs):
        input_path.unlink()


def model_payload(model: str) -> dict[str, object]:
    path = model_path(model)
    downloaded = path.exists()
    status_record = model_status(model)
    return {
        "name": model,
        "description": MODEL_DESCRIPTIONS[model],
        "downloaded": downloaded,
        "status": status_record.get("status") or ("downloaded" if downloaded else "missing"),
        "error": status_record.get("error"),
        "path": str(path),
        "size_bytes": directory_size(path) if downloaded else 0,
    }


def model_status(model: str) -> dict[str, str | None]:
    with _model_status_lock:
        return dict(_model_status.get(model, {}))


def require_model(model: str) -> str:
    if model not in MODELS:
        raise HTTPException(status_code=404, detail="Unknown model.")
    return model


def model_path(model: str) -> Path:
    return models_dir() / f"models--Systran--faster-whisper-{model}"


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def download_model_job(model: str) -> None:
    try:
        from faster_whisper import WhisperModel

        WhisperModel(model, device="cpu", compute_type="int8", download_root=str(models_dir()))
        with _model_status_lock:
            _model_status[model] = {"status": "downloaded", "error": None}
    except Exception as exc:  # noqa: BLE001 - model download failures should be visible in the UI.
        with _model_status_lock:
            _model_status[model] = {"status": "failed", "error": str(exc)}


def recover_interrupted_jobs() -> None:
    for job in db_list_jobs():
        if job.status in ACTIVE_STATUSES:
            failed_at = timestamp()
            update_job_status(
                job.id,
                "failed",
                failed_at,
                error="Interrupted by API restart before completion.",
                progress_message="Interrupted by API restart before completion.",
                completed_at=failed_at,
            )


def rescan_completed_outputs() -> int:
    known_outputs = list_output_dirs()
    added = 0
    for transcript_path in outputs_dir().glob("*/transcript.json"):
        output_dir = transcript_path.parent.resolve()
        if str(output_dir) in known_outputs:
            continue
        try:
            transcript = read_json(transcript_path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue

        stat = transcript_path.stat()
        scanned_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        source = Path(transcript.source) if transcript.source else Path(output_dir.name)
        job = JobRecord(
            id=scanned_job_id(output_dir),
            file_name=source.name or output_dir.name,
            input_path=str(source),
            output_dir=str(output_dir),
            status="completed",
            model="unknown",
            language=transcript.language,
            device="unknown",
            compute_type="unknown",
            task="transcribe",
            vad_filter=True,
            keep_audio=(output_dir / "audio.wav").exists(),
            created_at=scanned_at,
            updated_at=scanned_at,
            progress_message=STAGE_MESSAGES["completed"],
            started_at=scanned_at,
            completed_at=scanned_at,
        )
        insert_job(job)
        added += 1
    return added


def scanned_job_id(output_dir: Path) -> str:
    digest = hashlib.sha1(str(output_dir).encode("utf-8")).hexdigest()
    return f"scan-{digest[:24]}"


rescan_completed_outputs()
recover_interrupted_jobs()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aquill-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8091, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run(
        "revenge_transcriber.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
