# Revenge Transcriber

Local-first transcription and subtitle generation. The project is designed to keep working files, model downloads, caches, temporary files, and outputs on `D:\`.

## Storage Contract

The default project root is:

```text
D:\revenge-tour\transcriber
```

The app writes only under this root unless you explicitly pass another `D:\` output path.

Important directories:

```text
D:\revenge-tour\transcriber\models
D:\revenge-tour\transcriber\inputs
D:\revenge-tour\transcriber\outputs
D:\revenge-tour\transcriber\tmp
D:\revenge-tour\transcriber\cache
```

## Setup

From PowerShell:

```powershell
D:\revenge-tour\transcriber\scripts\setup.ps1
```

That creates a virtual environment at:

```text
D:\revenge-tour\transcriber\.venv
```

and installs the CLI in editable mode.

## Usage

Put media files under `D:\revenge-tour\transcriber\inputs`, then run:

```powershell
D:\revenge-tour\transcriber\scripts\transcribe.ps1 D:\revenge-tour\transcriber\inputs\sample.mp4
```

Outputs are written to a timestamped job directory under:

```text
D:\revenge-tour\transcriber\outputs
```

Generated files:

- `transcript.txt`
- `transcript.json`
- `subtitles.srt`
- `subtitles.vtt`
- extracted `audio.wav`, only when `--keep-audio` is passed

## CLI Options

```powershell
revenge-transcribe <input-file> --model small --language en --device auto --compute-type int8
```

Use `tiny` or `base` for faster first tests. Larger models are slower and require more disk space.

## API

Run:

```powershell
D:\revenge-tour\transcriber\scripts\serve-api.ps1 --host 127.0.0.1 --port 8091
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
- `GET /api/jobs/{job_id}/download/{txt|json|srt|vtt|audio}`
- `GET /api/jobs/{job_id}/archive`
- `POST /api/jobs/import`
- `GET /api/models`
- `POST /api/models/{model}/download`
- `DELETE /api/models/{model}`

The API accepts one active transcription worker by default.
Job history is stored in `D:\revenge-tour\transcriber\data\transcriber.db`.
Completed output folders are rescanned on API startup so older jobs can reappear.
Interrupted active jobs are marked failed on API startup so the queue does not get stuck after a restart.
Cancel requests work for queued jobs and running jobs. Running jobs stop at safe checkpoints during FFmpeg extraction, Whisper segment iteration, or before export writing, and temporary audio is cleaned up.
Completed jobs can be exported as ZIP archives containing a `manifest.json` plus available transcript, subtitle, JSON, and optional kept audio artifacts.
Archives can be imported back into local D-drive storage with `POST /api/jobs/import`. Import validates the archive manifest version, rejects unsafe ZIP member paths such as traversal entries, restores only known artifact filenames, and creates a new completed local job rather than overwriting an existing one.
The local web UI exposes the same archive flow with an Export action on completed jobs and an Import ZIP control in the intake panel.

## Requirements

- Python 3.10+
- FFmpeg available on `PATH`
- Enough free space on `D:\` for model downloads and generated audio

## Tests

Run the backend quality check with:

```powershell
D:\revenge-tour\transcriber\scripts\quality-backend.ps1
```

That command compiles the backend package and tests, then runs the focused `unittest` suite. The tests use fake transcription work and an isolated D-drive test root under `D:\revenge-tour\transcriber\tmp`.

This backend check does not download Whisper models or run real transcription.
