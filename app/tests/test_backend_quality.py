from __future__ import annotations

import os
import json
import shutil
import sqlite3
import threading
import time
import unittest
import uuid
import zipfile
from contextlib import closing
from pathlib import Path
from unittest import mock


TEST_ROOT = Path(__file__).resolve().parents[2] / "tmp" / "backend-quality-tests"
os.environ["TRANSCRIBER_ROOT"] = str(TEST_ROOT)

if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)

from revenge_transcriber import db, server  # noqa: E402
from revenge_transcriber.archive import ArchiveImportError, build_job_archive, import_job_archive, preview_job_archive  # noqa: E402
from revenge_transcriber.exceptions import JobCancelled  # noqa: E402
from revenge_transcriber.formatters import TranscriptResult, TranscriptSegment, read_json, write_all_outputs  # noqa: E402
from revenge_transcriber.lyrics import align_lyrics_to_transcript, lyric_lines_from_text  # noqa: E402
from revenge_transcriber.paths import tmp_dir  # noqa: E402
from revenge_transcriber.pipeline import TranscriptionOptions, run_transcription_job  # noqa: E402
from revenge_transcriber.records import JobRecord  # noqa: E402


class BackendQualityTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.addCleanup(self._clear_server_state)

    def test_database_initialise_migrates_progress_columns(self) -> None:
        db_file = db.db_path()
        db_file.unlink(missing_ok=True)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_file)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE jobs (
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
                    error TEXT
                )
                """
            )

        db.initialise_database()

        with closing(sqlite3.connect(db_file)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
        self.assertIn("progress_message", columns)
        self.assertIn("started_at", columns)
        self.assertIn("completed_at", columns)

        job = self._insert_job("migration-roundtrip", "queued")
        db.update_job_status(
            job.id,
            "extracting",
            "2026-06-21T20:00:00+00:00",
            progress_message="Migrated progress.",
            started_at="2026-06-21T20:00:00+00:00",
        )
        migrated = db.get_job(job.id)
        self.assertIsNotNone(migrated)
        assert migrated is not None
        self.assertEqual(migrated.progress_message, "Migrated progress.")
        self.assertEqual(migrated.started_at, "2026-06-21T20:00:00+00:00")
        self.assertIsNone(migrated.completed_at)

    def test_storage_status_reports_d_drive_paths(self) -> None:
        status = server.storage_status()

        expected_keys = {
            "project_root",
            "inputs_dir",
            "outputs_dir",
            "models_dir",
            "data_dir",
            "tmp_dir",
            "cache_dir",
        }
        self.assertEqual(set(status), expected_keys)
        for label, value in status.items():
            with self.subTest(label=label):
                self.assertTrue(str(Path(value).resolve()).startswith(str(TEST_ROOT)))

    def test_health_reports_storage_and_worker_state(self) -> None:
        db.initialise_database()
        health = server.health()

        self.assertEqual(health["status"], "ok")
        self.assertTrue(str(Path(str(health["root"])).resolve()).startswith(str(TEST_ROOT)))
        self.assertTrue(str(Path(str(health["database_path"])).resolve()).startswith(str(TEST_ROOT)))
        self.assertTrue(health["database_available"])
        self.assertFalse(health["worker_busy"])
        self.assertEqual(health["active_jobs"], 0)
        self.assertIsInstance(health["total_jobs"], int)

    def test_cancel_queued_job_marks_final_and_clears_future_state(self) -> None:
        blocking_id = f"test-blocking-{uuid.uuid4().hex}"
        queued_id = f"test-queued-{uuid.uuid4().hex}"
        release = threading.Event()

        blocking_job = self._insert_job(blocking_id, "queued")
        queued_job = self._insert_job(queued_id, "queued")

        def fake_runner(**kwargs: object) -> None:
            on_progress = kwargs.get("on_progress")
            if callable(on_progress):
                on_progress("extracting", "Holding worker.")
            release.wait(timeout=5)
            if callable(on_progress):
                on_progress("completed", "Released worker.")

        with mock.patch.object(server, "run_transcription_job", side_effect=fake_runner):
            server.submit_job(
                blocking_id,
                Path(blocking_job.input_path),
                Path(blocking_job.output_dir),
                TranscriptionOptions(model="tiny"),
            )
            self._wait_for_status(blocking_id, "extracting")
            server.submit_job(
                queued_id,
                Path(queued_job.input_path),
                Path(queued_job.output_dir),
                TranscriptionOptions(model="tiny"),
            )

            cancelled = server.cancel_job(queued_id)["job"]
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["progress_message"], "Cancelled before transcription started.")
            self.assertFalse(cancelled["can_cancel"])

            final = server.require_job(queued_id)
            self.assertEqual(final.status, "cancelled")
            self.assertIsNotNone(final.completed_at)
            self.assertFalse(server.job_future_running(queued_id))

            release.set()
            self._wait_for_final(blocking_id)

    def test_cancel_running_job_stops_at_checkpoint_and_becomes_deletable(self) -> None:
        job_id = f"test-running-{uuid.uuid4().hex}"
        ready = threading.Event()
        job = self._insert_job(job_id, "queued")

        def fake_runner(**kwargs: object) -> None:
            on_progress = kwargs.get("on_progress")
            should_cancel = kwargs.get("should_cancel")
            if callable(on_progress):
                on_progress("extracting", "Fake extraction started.")
            ready.set()
            for _ in range(100):
                if callable(should_cancel) and should_cancel():
                    raise JobCancelled("Fake cancellation checkpoint.")
                time.sleep(0.02)
            raise AssertionError("Cancellation checkpoint was not reached.")

        with mock.patch.object(server, "run_transcription_job", side_effect=fake_runner):
            server.submit_job(job_id, Path(job.input_path), Path(job.output_dir), TranscriptionOptions(model="tiny"))
            self.assertTrue(ready.wait(timeout=5))
            response = server.cancel_job(job_id)["job"]
            self.assertEqual(response["status"], "cancelled")
            progress_message = response["progress_message"] or ""
            self.assertTrue(
                progress_message.startswith("Cancellation requested")
                or progress_message == "Fake cancellation checkpoint.",
                progress_message,
            )

            final = self._wait_for_final(job_id)
            self.assertEqual(final.progress_message, "Fake cancellation checkpoint.")
            self.assertIsNotNone(final.started_at)
            self.assertIsNotNone(final.completed_at)

            public = server.public_job(final)
            self.assertFalse(public["can_cancel"])
            self.assertTrue(public["can_delete"])

    def test_pipeline_removes_temp_audio_when_cancelled_after_extraction(self) -> None:
        input_file = server.inputs_dir() / "cancel-after-extraction.txt"
        input_file.write_text("fixture", encoding="utf-8")
        job_name = f"pipeline-cancel-{uuid.uuid4().hex}"
        working_audio = tmp_dir() / f"{job_name}.wav"
        progress: list[tuple[str, str | None]] = []

        def fake_extract(_input: Path, output: Path, **_kwargs: object) -> Path:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("temporary wav placeholder", encoding="utf-8")
            return output

        with (
            mock.patch("revenge_transcriber.pipeline.extract_audio", side_effect=fake_extract),
            mock.patch(
                "revenge_transcriber.pipeline.transcribe_audio",
                side_effect=JobCancelled("Cancelled while transcribing audio."),
            ),
        ):
            with self.assertRaises(JobCancelled):
                run_transcription_job(
                    input_file=input_file,
                    output_parent=server.outputs_dir(),
                    options=TranscriptionOptions(model="tiny"),
                    job_name=job_name,
                    on_progress=lambda stage, message: progress.append((stage, message)),
                )

        self.assertFalse(working_audio.exists())
        self.assertEqual(progress[0][0], "extracting")
        self.assertEqual(progress[1][0], "transcribing")

    def test_completed_job_archive_contains_manifest_and_available_artifacts(self) -> None:
        job = self._insert_job(f"test-archive-{uuid.uuid4().hex}", "completed")
        output_dir = Path(job.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "transcript.txt").write_text("hello world\n", encoding="utf-8")
        (output_dir / "transcript.json").write_text('{"text": "hello world"}\n', encoding="utf-8")
        (output_dir / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nhello world\n", encoding="utf-8")
        (output_dir / "subtitles.vtt").write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello world\n", encoding="utf-8")

        archive_path = build_job_archive(job)
        self.addCleanup(archive_path.unlink, missing_ok=True)

        self.assertTrue(str(archive_path).startswith(str(TEST_ROOT)))
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            self.assertEqual(
                names,
                {
                    "manifest.json",
                    "transcript.txt",
                    "transcript.json",
                    "subtitles.srt",
                    "subtitles.vtt",
                },
            )
            manifest = archive.read("manifest.json").decode("utf-8")

        self.assertIn('"archive_version": 1', manifest)
        self.assertIn(job.id, manifest)
        self.assertIn('"artifact": "txt"', manifest)
        public = server.public_job(job)
        self.assertEqual(public["archive_url"], f"/api/jobs/{job.id}/archive")

    def test_archive_endpoint_rejects_unfinished_jobs(self) -> None:
        job = self._insert_job(f"test-archive-queued-{uuid.uuid4().hex}", "queued")

        with self.assertRaises(Exception) as raised:
            server.download_job_archive(job.id)

        self.assertEqual(getattr(raised.exception, "status_code", None), 409)

    def test_import_archive_restores_artifacts_and_preserves_job_metadata(self) -> None:
        original = self._insert_job(f"test-import-source-{uuid.uuid4().hex}", "completed")
        original.file_name = "meeting-notes.mp3"
        original.model = "base"
        original.language = "cy"
        original.device = "cpu"
        original.compute_type = "int8"
        original.task = "translate"
        original.vad_filter = False
        original.keep_audio = True
        output_dir = Path(original.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "transcript.txt").write_text("croeso\n", encoding="utf-8")
        (output_dir / "transcript.json").write_text('{"text": "croeso"}\n', encoding="utf-8")
        (output_dir / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\ncroeso\n", encoding="utf-8")
        (output_dir / "audio.wav").write_bytes(b"fake wav")

        archive_path = build_job_archive(original)
        self.addCleanup(archive_path.unlink, missing_ok=True)
        imported = import_job_archive(archive_path, "2026-06-22T10:00:00+00:00")

        self.assertNotEqual(imported.id, original.id)
        self.assertEqual(imported.status, "completed")
        self.assertEqual(imported.file_name, "meeting-notes.mp3")
        self.assertEqual(imported.model, "base")
        self.assertEqual(imported.language, "cy")
        self.assertEqual(imported.device, "cpu")
        self.assertEqual(imported.compute_type, "int8")
        self.assertEqual(imported.task, "translate")
        self.assertFalse(imported.vad_filter)
        self.assertTrue(imported.keep_audio)
        self.assertIn(original.id, imported.progress_message or "")
        self.assertTrue(str(Path(imported.output_dir).resolve()).startswith(str(TEST_ROOT)))
        self.assertTrue(str(Path(imported.input_path).resolve()).startswith(str(TEST_ROOT)))
        self.assertEqual((Path(imported.output_dir) / "transcript.txt").read_text(encoding="utf-8"), "croeso\n")
        self.assertEqual((Path(imported.output_dir) / "audio.wav").read_bytes(), b"fake wav")

    def test_preview_archive_reports_metadata_without_restoring(self) -> None:
        before = {path.resolve() for path in server.outputs_dir().glob("*")}
        original = self._insert_job(f"test-preview-source-{uuid.uuid4().hex}", "completed")
        original.file_name = "preview-meeting.mp3"
        original.model = "base"
        original.language = "en"
        original.task = "translate"
        output_dir = Path(original.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "transcript.txt").write_text("hello\n", encoding="utf-8")
        (output_dir / "transcript.json").write_text('{"text": "hello"}\n', encoding="utf-8")

        archive_path = build_job_archive(original)
        self.addCleanup(archive_path.unlink, missing_ok=True)
        preview = preview_job_archive(archive_path)

        after = {path.resolve() for path in server.outputs_dir().glob("*")}
        self.assertEqual(after, before | {output_dir.resolve()})
        self.assertEqual(preview["archive_version"], 1)
        self.assertEqual(preview["source_job_id"], original.id)
        self.assertEqual(preview["file_name"], "preview-meeting.mp3")
        self.assertEqual(preview["model"], "base")
        self.assertEqual(preview["language"], "en")
        self.assertEqual(preview["task"], "translate")
        self.assertEqual([entry["artifact"] for entry in preview["artifacts"]], ["txt", "json"])

    def test_import_archive_rejects_path_traversal_members(self) -> None:
        archive_path = tmp_dir() / f"path-traversal-{uuid.uuid4().hex}.zip"
        self.addCleanup(archive_path.unlink, missing_ok=True)
        manifest = self._archive_manifest(
            included_artifacts=[{"artifact": "txt", "file_name": "transcript.txt", "size_bytes": 4}]
        )
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("manifest.json", manifest)
            archive.writestr("../transcript.txt", "nope")

        with self.assertRaises(ArchiveImportError) as raised:
            import_job_archive(archive_path, "2026-06-22T10:00:00+00:00")

        self.assertIn("Unsafe archive member path", str(raised.exception))

    def test_import_archive_rejects_missing_or_malformed_manifest(self) -> None:
        missing_manifest = tmp_dir() / f"missing-manifest-{uuid.uuid4().hex}.zip"
        malformed_manifest = tmp_dir() / f"bad-manifest-{uuid.uuid4().hex}.zip"
        self.addCleanup(missing_manifest.unlink, missing_ok=True)
        self.addCleanup(malformed_manifest.unlink, missing_ok=True)
        with zipfile.ZipFile(missing_manifest, "w") as archive:
            archive.writestr("transcript.txt", "hello")
        with zipfile.ZipFile(malformed_manifest, "w") as archive:
            archive.writestr("manifest.json", "{")

        with self.assertRaises(ArchiveImportError) as missing:
            import_job_archive(missing_manifest, "2026-06-22T10:00:00+00:00")
        with self.assertRaises(ArchiveImportError) as malformed:
            import_job_archive(malformed_manifest, "2026-06-22T10:00:00+00:00")

        self.assertIn("manifest", str(missing.exception).lower())
        self.assertIn("manifest", str(malformed.exception).lower())

    def test_import_archive_rejects_unsupported_archive_version(self) -> None:
        archive_path = tmp_dir() / f"unsupported-version-{uuid.uuid4().hex}.zip"
        self.addCleanup(archive_path.unlink, missing_ok=True)
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("manifest.json", self._archive_manifest(version=99))

        with self.assertRaises(ArchiveImportError) as raised:
            import_job_archive(archive_path, "2026-06-22T10:00:00+00:00")

        self.assertIn("Unsupported archive version", str(raised.exception))

    def test_import_archive_rejects_invalid_zip(self) -> None:
        archive_path = tmp_dir() / f"not-a-zip-{uuid.uuid4().hex}.zip"
        self.addCleanup(archive_path.unlink, missing_ok=True)
        archive_path.write_text("not actually a zip", encoding="utf-8")

        with self.assertRaises(ArchiveImportError) as raised:
            import_job_archive(archive_path, "2026-06-22T10:00:00+00:00")

        self.assertIn("valid ZIP", str(raised.exception))

    def test_import_archive_cleans_partial_output_on_artifact_error(self) -> None:
        before = {path.resolve() for path in server.outputs_dir().glob("*")}
        archive_path = tmp_dir() / f"partial-import-{uuid.uuid4().hex}.zip"
        self.addCleanup(archive_path.unlink, missing_ok=True)
        manifest = self._archive_manifest(
            included_artifacts=[
                {"artifact": "txt", "file_name": "transcript.txt", "size_bytes": 6},
                {"artifact": "bogus", "file_name": "bogus.bin", "size_bytes": 1},
            ]
        )
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("manifest.json", manifest)
            archive.writestr("transcript.txt", "hello\n")

        with self.assertRaises(ArchiveImportError) as raised:
            import_job_archive(archive_path, "2026-06-22T10:00:00+00:00")

        after = {path.resolve() for path in server.outputs_dir().glob("*")}
        self.assertIn("Unsupported artifact entry", str(raised.exception))
        self.assertEqual(after, before)

    def test_lyrics_cleanup_removes_section_labels(self) -> None:
        lines = lyric_lines_from_text(
            """
            Lyrics:
            [Intro]
            First real line

            [Chorus]
            Second real line
            [End]
            """
        )

        self.assertEqual(lines, ["First real line", "Second real line"])

    def test_lyrics_alignment_distributes_more_lines_than_segments(self) -> None:
        base = TranscriptResult(
            source="song.wav",
            language="en",
            duration=12.0,
            segments=[TranscriptSegment(index=1, start=0.0, end=12.0, text="bad transcript")],
        )

        aligned = align_lyrics_to_transcript(base, "Line one\nLine two\nLine three")

        self.assertEqual([segment.text for segment in aligned.segments], ["Line one", "Line two", "Line three"])
        self.assertEqual([(segment.start, segment.end) for segment in aligned.segments], [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0)])

    def test_lyrics_endpoint_regenerates_transcript_and_subtitles(self) -> None:
        job = self._insert_job(f"test-lyrics-{uuid.uuid4().hex}", "completed")
        output_dir = Path(job.output_dir)
        write_all_outputs(
            TranscriptResult(
                source=job.input_path,
                language="en",
                duration=10.0,
                segments=[
                    TranscriptSegment(index=1, start=0.0, end=5.0, text="mumbled opening"),
                    TranscriptSegment(index=2, start=5.0, end=10.0, text="mumbled ending"),
                ],
            ),
            output_dir,
        )

        payload = server.align_job_lyrics(
            job.id,
            server.LyricsAlignmentRequest(lyrics="Lyrics:\n[Verse]\nActual first line\nActual second line"),
        )

        self.assertEqual(payload["line_count"], 2)
        self.assertTrue(payload["has_original_transcript"])
        transcript = read_json(output_dir / "transcript.json")
        self.assertEqual([segment.text for segment in transcript.segments], ["Actual first line", "Actual second line"])
        self.assertIn("mumbled opening", (output_dir / "transcript.original.txt").read_text(encoding="utf-8"))
        self.assertTrue((output_dir / "transcript.original.json").exists())
        self.assertTrue((output_dir / "subtitles.original.srt").exists())
        self.assertTrue((output_dir / "subtitles.original.vtt").exists())
        self.assertIn("Actual first line", (output_dir / "subtitles.srt").read_text(encoding="utf-8"))
        self.assertIn("Actual second line", (output_dir / "subtitles.vtt").read_text(encoding="utf-8"))
        updated = server.require_job(job.id)
        self.assertEqual(updated.progress_message, "Lyrics aligned into 2 timed lines.")
        self.assertTrue(server.public_job(updated)["has_original_transcript"])

    def test_lyrics_preview_does_not_write_outputs_or_backups(self) -> None:
        job = self._insert_job(f"test-lyrics-preview-{uuid.uuid4().hex}", "completed")
        output_dir = Path(job.output_dir)
        write_all_outputs(
            TranscriptResult(
                source=job.input_path,
                language="en",
                duration=8.0,
                segments=[TranscriptSegment(index=1, start=0.0, end=8.0, text="rough words")],
            ),
            output_dir,
        )
        original_text = (output_dir / "transcript.txt").read_text(encoding="utf-8")

        payload = server.preview_job_lyrics(job.id, server.LyricsAlignmentRequest(lyrics="Clean line one\nClean line two"))

        self.assertEqual(payload["line_count"], 2)
        self.assertFalse(payload["has_original_transcript"])
        preview = payload["transcript"]
        self.assertIsInstance(preview, dict)
        self.assertEqual([segment["text"] for segment in preview["segments"]], ["Clean line one", "Clean line two"])
        self.assertEqual((output_dir / "transcript.txt").read_text(encoding="utf-8"), original_text)
        self.assertFalse((output_dir / "transcript.original.json").exists())

    def test_restore_original_transcript_restores_backed_up_outputs(self) -> None:
        job = self._insert_job(f"test-lyrics-restore-{uuid.uuid4().hex}", "completed")
        output_dir = Path(job.output_dir)
        write_all_outputs(
            TranscriptResult(
                source=job.input_path,
                language="en",
                duration=6.0,
                segments=[TranscriptSegment(index=1, start=0.0, end=6.0, text="rough original")],
            ),
            output_dir,
        )
        server.align_job_lyrics(job.id, server.LyricsAlignmentRequest(lyrics="Corrected lyric"))

        payload = server.restore_original_transcript(job.id)

        self.assertEqual(set(payload["restored_artifacts"]), {"transcript.txt", "transcript.json", "subtitles.srt", "subtitles.vtt"})
        self.assertTrue(payload["has_original_transcript"])
        restored = read_json(output_dir / "transcript.json")
        self.assertEqual([segment.text for segment in restored.segments], ["rough original"])
        self.assertIn("rough original", (output_dir / "subtitles.srt").read_text(encoding="utf-8"))
        updated = server.require_job(job.id)
        self.assertEqual(updated.progress_message, "Original transcript restored (4 artifacts).")

    def test_lyrics_endpoint_rejects_empty_cleaned_lyrics(self) -> None:
        job = self._insert_job(f"test-empty-lyrics-{uuid.uuid4().hex}", "completed")
        write_all_outputs(
            TranscriptResult(
                source=job.input_path,
                language="en",
                duration=1.0,
                segments=[TranscriptSegment(index=1, start=0.0, end=1.0, text="placeholder")],
            ),
            Path(job.output_dir),
        )

        with self.assertRaises(Exception) as raised:
            server.align_job_lyrics(job.id, server.LyricsAlignmentRequest(lyrics="[Intro]\n[End]"))

        self.assertEqual(getattr(raised.exception, "status_code", None), 400)

    def _insert_job(self, job_id: str, status: str) -> JobRecord:
        now = server.timestamp()
        input_path = server.inputs_dir() / f"{job_id}.txt"
        output_dir = server.outputs_dir() / job_id
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text("fixture", encoding="utf-8")
        job = JobRecord(
            id=job_id,
            file_name=input_path.name,
            input_path=str(input_path),
            output_dir=str(output_dir),
            status=status,  # type: ignore[arg-type]
            model="tiny",
            language="en",
            device="cpu",
            compute_type="int8",
            task="transcribe",
            vad_filter=True,
            keep_audio=False,
            created_at=now,
            updated_at=now,
            progress_message=server.STAGE_MESSAGES[status],
        )
        db.insert_job(job)
        self.addCleanup(db.delete_job, job.id)
        input_path.parent.mkdir(parents=True, exist_ok=True)
        return job

    def _archive_manifest(
        self,
        version: int = 1,
        included_artifacts: list[dict[str, object]] | None = None,
    ) -> str:
        return json.dumps(
            {
                "archive_version": version,
                "job": {
                    "id": "source-job",
                    "file_name": "source.wav",
                    "model": "tiny",
                    "language": "en",
                    "device": "cpu",
                    "compute_type": "int8",
                    "task": "transcribe",
                    "vad_filter": True,
                    "keep_audio": False,
                },
                "included_artifacts": included_artifacts or [],
            }
        )

    def _wait_for_status(self, job_id: str, status: str, timeout: float = 3) -> JobRecord:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = server.require_job(job_id)
            if job.status == status:
                return job
            time.sleep(0.02)
        self.fail(f"Timed out waiting for {job_id} to become {status}.")

    def _wait_for_final(self, job_id: str, timeout: float = 3) -> JobRecord:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = server.require_job(job_id)
            if job.status in server.FINAL_STATUSES and not server.job_future_running(job_id):
                return job
            time.sleep(0.02)
        self.fail(f"Timed out waiting for {job_id} to finish.")

    def _clear_server_state(self) -> None:
        with server._futures_lock:
            events = list(server._cancel_events.values())
            futures = list(server._futures.values())
            server._cancel_events.clear()
            server._futures.clear()
        for event in events:
            event.set()
        for future in futures:
            future.cancel()


if __name__ == "__main__":
    unittest.main()
