# Aquill

Source-available, local-first transcription and subtitle generation. The project is designed to keep working files, model downloads, caches, temporary files, and outputs on `D:\`.

Licensed under the PolyForm Noncommercial License 1.0.0. Personal and noncommercial local use is allowed; commercial hosting, resale, paid subscription use, or inclusion in a paid transcription/conversion service is not allowed without a separate commercial license.

## Storage Contract

Use a D-drive project root, for example:

```text
D:\Projects\aquill
```

The scripts resolve the active project root from their own location. The app writes only under that D-drive checkout unless you explicitly pass another `D:\` output path.

Important directories:

```text
models
inputs
outputs
tmp
cache
```

## Setup

From PowerShell:

```powershell
.\scripts\setup.ps1
```

That creates a virtual environment at:

```text
.venv
```

and installs the CLI in editable mode.

## Usage

Put media files under `inputs`, then run:

```powershell
.\scripts\transcribe.ps1 .\inputs\sample.mp4
```

Outputs are written to a timestamped job directory under:

```text
outputs
```

Generated files:

- `transcript.txt`
- `transcript.json`
- `subtitles.srt`
- `subtitles.vtt`
- extracted `audio.wav`, only when `--keep-audio` is passed

## CLI Options

```powershell
aquill <input-file> --model small --language en --device auto --compute-type int8
```

Use `tiny` or `base` for faster first tests. Larger models are slower and require more disk space.

## API

Run:

```powershell
.\scripts\serve-api.ps1 --host 127.0.0.1 --port 8091
```

Endpoints:

- `GET /api/health`
- `GET /api/jobs`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/retry`
- `DELETE /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/open-output`
- `GET /api/jobs/{job_id}/transcript`
- `PUT /api/jobs/{job_id}/transcript`
- `POST /api/jobs/{job_id}/transcript/restore-original`
- `POST /api/jobs/{job_id}/lyrics/preview`
- `POST /api/jobs/{job_id}/lyrics`
- `GET /api/jobs/{job_id}/download/{txt|json|srt|vtt|audio}`
- `GET /api/jobs/{job_id}/archive`
- `POST /api/jobs/import/preview`
- `POST /api/jobs/import`
- `GET /api/models`
- `GET /api/system/storage`
- `POST /api/models/{model}/download`
- `DELETE /api/models/{model}`

The API accepts one active transcription worker by default.
The health endpoint reports API status, project root, database path and availability, worker busy state, active jobs, and total jobs.
Job history is stored in `data\transcriber.db`.
Completed output folders are rescanned on API startup so older jobs can reappear.
Interrupted active jobs are marked failed on API startup so the queue does not get stuck after a restart.
Cancel requests work for queued jobs and running jobs. Running jobs stop at safe checkpoints during FFmpeg extraction, Whisper segment iteration, or before export writing, and temporary audio is cleaned up.
Completed jobs can be exported as ZIP archives containing a `manifest.json` plus available transcript, subtitle, JSON, and optional kept audio artifacts.
Known lyrics can be previewed with `POST /api/jobs/{job_id}/lyrics/preview` for a completed job, then applied with `POST /api/jobs/{job_id}/lyrics`. The API removes simple section labels such as `[Chorus]`, aligns lyric lines to the job duration or existing segment timing, backs up the original TXT, JSON, SRT, and VTT artifacts once, and regenerates the normal outputs. `POST /api/jobs/{job_id}/transcript/restore-original` restores those backed-up artifacts.
Archives can be imported back into local D-drive storage with `POST /api/jobs/import`. Import validates the archive manifest version, rejects unsafe ZIP member paths such as traversal entries, restores only known artifact filenames, and creates a new completed local job rather than overwriting an existing one.
The import preview endpoint validates an archive and returns source job metadata plus artifact names without restoring files.
The local web UI exposes the same archive flow with an Export action on completed jobs and an Import ZIP preview/import control in the intake panel. The transcript panel also exposes lyrics preview, apply, and restore controls for rough song transcripts when the user already has the correct words. The upload panel includes a Song preset for music-oriented defaults.
The storage endpoint reports the active project, input, output, model, data, temp, and cache directories so the UI can show that runtime storage is pinned to `D:\`.

## Requirements

- Python 3.10+
- FFmpeg available on `PATH`
- Enough free space on `D:\` for model downloads and generated audio

## Tests

Run the backend quality check with:

```powershell
.\scripts\quality-backend.ps1
```

That command compiles the backend package and tests, then runs the focused `unittest` suite. The tests use fake transcription work and an isolated D-drive test root under `tmp`.

This backend check does not download Whisper models or run real transcription.
