from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from .paths import data_dir
from .records import JobRecord, JobStatus


DB_LOCK = threading.Lock()
UNSET = object()


def db_path() -> Path:
    path = data_dir() / "transcriber.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def initialise_database() -> None:
    with closing(connect()) as connection, connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                input_path TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                status TEXT NOT NULL,
                model TEXT NOT NULL,
                language TEXT,
                device TEXT NOT NULL,
                compute_type TEXT NOT NULL,
                task TEXT NOT NULL,
                vad_filter INTEGER NOT NULL,
                keep_audio INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                progress_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                error TEXT
            )
            """
        )
        ensure_columns(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_output_dir ON jobs(output_dir)")


def ensure_columns(connection: sqlite3.Connection) -> None:
    columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
    additions = {
        "progress_message": "TEXT",
        "started_at": "TEXT",
        "completed_at": "TEXT",
    }
    for name, column_type in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE jobs ADD COLUMN {name} {column_type}")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(db_path(), timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def insert_job(job: JobRecord) -> None:
    with DB_LOCK, closing(connect()) as connection, connection:
        connection.execute(
            """
            INSERT INTO jobs (
                id, file_name, input_path, output_dir, status, model, language,
                device, compute_type, task, vad_filter, keep_audio, created_at,
                updated_at, progress_message, started_at, completed_at, error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                file_name=excluded.file_name,
                input_path=excluded.input_path,
                output_dir=excluded.output_dir,
                status=excluded.status,
                model=excluded.model,
                language=excluded.language,
                device=excluded.device,
                compute_type=excluded.compute_type,
                task=excluded.task,
                vad_filter=excluded.vad_filter,
                keep_audio=excluded.keep_audio,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                progress_message=excluded.progress_message,
                started_at=excluded.started_at,
                completed_at=excluded.completed_at,
                error=excluded.error
            """,
            job_to_row(job),
        )


def update_job_status(
    job_id: str,
    status: JobStatus,
    updated_at: str,
    error: str | None | object = UNSET,
    progress_message: str | None | object = UNSET,
    started_at: str | None | object = UNSET,
    completed_at: str | None | object = UNSET,
) -> None:
    assignments = ["status = ?", "updated_at = ?"]
    values: list[object] = [status, updated_at]
    optional_fields = {
        "error": error,
        "progress_message": progress_message,
        "started_at": started_at,
        "completed_at": completed_at,
    }
    for field, value in optional_fields.items():
        if value is UNSET:
            continue
        assignments.append(f"{field} = ?")
        values.append(value)
    values.append(job_id)

    with DB_LOCK, closing(connect()) as connection, connection:
        connection.execute(
            f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?",
            tuple(values),
        )


def delete_job(job_id: str) -> None:
    with DB_LOCK, closing(connect()) as connection, connection:
        connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def get_job(job_id: str) -> JobRecord | None:
    with closing(connect()) as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_job(row) if row else None


def list_jobs() -> list[JobRecord]:
    with closing(connect()) as connection:
        rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [row_to_job(row) for row in rows]


def list_output_dirs() -> set[str]:
    with closing(connect()) as connection:
        rows = connection.execute("SELECT output_dir FROM jobs").fetchall()
    return {str(row["output_dir"]) for row in rows}


def job_to_row(job: JobRecord) -> tuple[object, ...]:
    return (
        job.id,
        job.file_name,
        job.input_path,
        job.output_dir,
        job.status,
        job.model,
        job.language,
        job.device,
        job.compute_type,
        job.task,
        int(job.vad_filter),
        int(job.keep_audio),
        job.created_at,
        job.updated_at,
        job.progress_message,
        job.started_at,
        job.completed_at,
        job.error,
    )


def row_to_job(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=str(row["id"]),
        file_name=str(row["file_name"]),
        input_path=str(row["input_path"]),
        output_dir=str(row["output_dir"]),
        status=str(row["status"]),  # type: ignore[arg-type]
        model=str(row["model"]),
        language=row["language"],
        device=str(row["device"]),
        compute_type=str(row["compute_type"]),
        task=str(row["task"]),
        vad_filter=bool(row["vad_filter"]),
        keep_audio=bool(row["keep_audio"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        progress_message=row["progress_message"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        error=row["error"],
    )
