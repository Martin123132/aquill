from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from dataclasses import asdict
from pathlib import Path

from .naming import make_job_name, safe_file_name
from .paths import inputs_dir, outputs_dir, tmp_dir
from .records import JobRecord


ARCHIVE_FILES = {
    "txt": "transcript.txt",
    "json": "transcript.json",
    "srt": "subtitles.srt",
    "vtt": "subtitles.vtt",
    "audio": "audio.wav",
}


class ArchiveImportError(ValueError):
    """Raised when an archive cannot be safely imported."""


def build_job_archive(job: JobRecord) -> Path:
    output_dir = Path(job.output_dir).resolve()
    archive_path = tmp_dir() / f"{job.id}-{uuid.uuid4().hex}-archive.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    included: list[dict[str, object]] = []
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for artifact, file_name in ARCHIVE_FILES.items():
            path = output_dir / file_name
            if not path.exists() or not path.is_file():
                continue
            archive.write(path, file_name)
            included.append(
                {
                    "artifact": artifact,
                    "file_name": file_name,
                    "size_bytes": path.stat().st_size,
                }
            )

        manifest = {
            "archive_version": 1,
            "job": asdict(job),
            "included_artifacts": included,
        }
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        )

    return archive_path


def import_job_archive(archive_path: Path, imported_at: str) -> JobRecord:
    archive_path = archive_path.resolve()
    output_dir: Path | None = None
    try:
        with zipfile.ZipFile(archive_path) as archive:
            manifest = read_manifest(archive)
            original_job = manifest_job(manifest)
            included = manifest_artifacts(manifest)
            validate_archive_members(archive)

            new_id = f"import-{uuid.uuid4().hex}"
            file_name = safe_file_name(str(original_job.get("file_name") or "imported-media"))
            output_dir = unique_output_dir(file_name)
            output_dir.mkdir(parents=True, exist_ok=False)

            for entry in included:
                artifact = str(entry.get("artifact") or "")
                file_name_in_archive = str(entry.get("file_name") or "")
                expected_name = ARCHIVE_FILES.get(artifact)
                if expected_name is None or file_name_in_archive != expected_name:
                    raise ArchiveImportError(f"Unsupported artifact entry: {artifact or file_name_in_archive}")
                if expected_name not in archive.namelist():
                    raise ArchiveImportError(f"Archive is missing artifact: {expected_name}")
                target = output_dir / expected_name
                target.write_bytes(archive.read(expected_name))
    except ArchiveImportError:
        if output_dir is not None:
            shutil.rmtree(output_dir, ignore_errors=True)
        raise
    except zipfile.BadZipFile as exc:
        if output_dir is not None:
            shutil.rmtree(output_dir, ignore_errors=True)
        raise ArchiveImportError("Archive is not a valid ZIP file.") from exc
    except (KeyError, json.JSONDecodeError, TypeError) as exc:
        if output_dir is not None:
            shutil.rmtree(output_dir, ignore_errors=True)
        raise ArchiveImportError("Archive manifest is missing or malformed.") from exc

    marker_path = inputs_dir() / f"{new_id}-{file_name}.imported.txt"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    original_id = str(original_job.get("id") or "unknown")
    marker_path.write_text(
        f"Imported from archive job {original_id} at {imported_at}.\n",
        encoding="utf-8",
    )

    return JobRecord(
        id=new_id,
        file_name=file_name,
        input_path=str(marker_path),
        output_dir=str(output_dir),
        status="completed",
        model=str(original_job.get("model") or "unknown"),
        language=optional_str(original_job.get("language")),
        device=str(original_job.get("device") or "unknown"),
        compute_type=str(original_job.get("compute_type") or "unknown"),
        task=str(original_job.get("task") or "transcribe"),
        vad_filter=bool(original_job.get("vad_filter", True)),
        keep_audio=(output_dir / ARCHIVE_FILES["audio"]).exists(),
        created_at=imported_at,
        updated_at=imported_at,
        progress_message=f"Imported from archive job {original_id}.",
        started_at=imported_at,
        completed_at=imported_at,
    )


def preview_job_archive(archive_path: Path) -> dict[str, object]:
    archive_path = archive_path.resolve()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            manifest = read_manifest(archive)
            original_job = manifest_job(manifest)
            included = manifest_artifacts(manifest)
            validate_archive_members(archive)
            for entry in included:
                artifact = str(entry.get("artifact") or "")
                file_name_in_archive = str(entry.get("file_name") or "")
                expected_name = ARCHIVE_FILES.get(artifact)
                if expected_name is None or file_name_in_archive != expected_name:
                    raise ArchiveImportError(f"Unsupported artifact entry: {artifact or file_name_in_archive}")
                if expected_name not in archive.namelist():
                    raise ArchiveImportError(f"Archive is missing artifact: {expected_name}")
    except zipfile.BadZipFile as exc:
        raise ArchiveImportError("Archive is not a valid ZIP file.") from exc
    except (KeyError, json.JSONDecodeError, TypeError) as exc:
        raise ArchiveImportError("Archive manifest is missing or malformed.") from exc

    return {
        "archive_version": manifest["archive_version"],
        "source_job_id": str(original_job.get("id") or "unknown"),
        "file_name": safe_file_name(str(original_job.get("file_name") or "imported-media")),
        "model": str(original_job.get("model") or "unknown"),
        "language": optional_str(original_job.get("language")),
        "task": str(original_job.get("task") or "transcribe"),
        "artifacts": included,
    }


def read_manifest(archive: zipfile.ZipFile) -> dict[str, object]:
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ArchiveImportError("Archive manifest is malformed.")
    version = manifest.get("archive_version")
    if version != 1:
        raise ArchiveImportError(f"Unsupported archive version: {version!r}")
    return manifest


def manifest_job(manifest: dict[str, object]) -> dict[str, object]:
    job = manifest.get("job")
    if not isinstance(job, dict):
        raise ArchiveImportError("Archive manifest is missing job metadata.")
    return job


def manifest_artifacts(manifest: dict[str, object]) -> list[dict[str, object]]:
    artifacts = manifest.get("included_artifacts")
    if not isinstance(artifacts, list):
        raise ArchiveImportError("Archive manifest is missing artifact metadata.")
    if not artifacts:
        raise ArchiveImportError("Archive does not contain importable artifacts.")
    parsed: list[dict[str, object]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ArchiveImportError("Archive artifact metadata is malformed.")
        parsed.append(artifact)
    return parsed


def validate_archive_members(archive: zipfile.ZipFile) -> None:
    allowed = {"manifest.json", *ARCHIVE_FILES.values()}
    for info in archive.infolist():
        name = info.filename
        normalized = name.replace("\\", "/")
        path = Path(normalized)
        if (
            name != normalized
            or normalized.startswith("/")
            or path.is_absolute()
            or ".." in path.parts
            or normalized not in allowed
        ):
            raise ArchiveImportError(f"Unsafe archive member path: {name}")


def unique_output_dir(file_name: str) -> Path:
    base = outputs_dir() / make_job_name(Path(f"imported-{file_name}"))
    if not base.exists():
        return base
    for _ in range(100):
        candidate = outputs_dir() / f"{base.name}-{uuid.uuid4().hex[:8]}"
        if not candidate.exists():
            return candidate
    raise ArchiveImportError("Could not allocate an output folder for the imported archive.")


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
