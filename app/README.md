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

For the native Windows launcher and packaging tools:

```powershell
.\scripts\setup-packaging.ps1
.\scripts\start-desktop.ps1
```

The desktop window contains the compiled workbench and private loopback API. Closing it stops the local API thread. Installed builds use `D:\Aquill` for writable data and do not place media, models, transcripts, databases, caches, or temp files beside the executable.

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

The normal local app command builds the interface and serves both the UI and API from one process at `http://127.0.0.1:5190`:

```powershell
.\scripts\start-local.ps1
```

For standalone API development, run:

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
- `GET /api/jobs/{job_id}/media`
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
Interrupted active jobs are marked failed on API startup so the queue does not get stuck after a restart. Their abandoned temporary WAV is removed while the original input is preserved for one-click retry.
Cancel requests work for queued jobs and running jobs. Running jobs stop at safe checkpoints during FFmpeg extraction, Whisper segment iteration, or before export writing, and temporary audio is cleaned up.
Completed jobs can be exported as ZIP archives containing a `manifest.json` plus available transcript, subtitle, JSON, and optional kept audio artifacts.
Known lyrics can be previewed with `POST /api/jobs/{job_id}/lyrics/preview` for a completed job, then applied with `POST /api/jobs/{job_id}/lyrics`. The API removes simple section labels such as `[Chorus]`, aligns lyric lines to the job duration or existing segment timing, backs up the original TXT, JSON, SRT, and VTT artifacts once, and regenerates the normal outputs. `POST /api/jobs/{job_id}/transcript/restore-original` restores those backed-up artifacts.
`PUT /api/jobs/{job_id}/transcript` accepts the original text-only segment update shape and full structural updates containing text, start, and end values. Structural saves renumber cues, reject duplicate indexes, partial timing data, overlaps, zero-length cues, and cues beyond the media duration, then regenerate TXT, JSON, SRT, and VTT together.
`GET /api/jobs/{job_id}/media` streams the retained `audio.wav` when available, otherwise it streams a supported original upload from the local `inputs` directory. The endpoint rejects missing media and paths outside Aquill's configured D-drive input/output roots.
Archives can be imported back into local D-drive storage with `POST /api/jobs/import`. Import validates the archive manifest version, rejects unsafe ZIP member paths such as traversal entries, restores only known artifact filenames, and creates a new completed local job rather than overwriting an existing one.
The import preview endpoint validates an archive and returns source job metadata plus artifact names without restoring files.
The local web UI exposes the same archive flow with an Export action on completed jobs and an Import ZIP preview/import control in the intake panel. The transcript panel also exposes lyrics preview, apply, and restore controls for rough song transcripts when the user already has the correct words. Subtitle quality controls report line length, line count, characters per second, and cue-duration warnings against locally persisted thresholds. `Wrap cues` changes the undoable draft first; saving regenerates the normal TXT, JSON, SRT, and VTT outputs. Available local media can be played in the editor, with the matching cue highlighted as playback moves. The upload panel includes a Song preset for music-oriented defaults.
The storage endpoint reports the active project, input, output, model, data, temp, and cache directories so the UI can show that runtime storage is pinned to `D:\`.

## Requirements

- Python 3.10+
- FFmpeg available on `PATH`
- Enough free space on `D:\` for model downloads and generated audio

## Tests

Run all backend tests, frontend tests, and the production web build with:

```powershell
.\scripts\quality-all.ps1
```

Run only the backend quality check with:

```powershell
.\scripts\quality-backend.ps1
```

The backend command compiles the package and tests, then runs the focused `unittest` suite. The frontend suite uses mocked local API responses and covers split/merge, timing, find/replace, undo/redo, subtitle wrapping and diagnostics, synchronized playback state, transcript/lyrics editing, archive import, interrupted-job retry, and upload errors. Tests use fake transcription work and D-drive project storage.

This backend check does not download Whisper models or run real transcription.

Build and verify the self-contained Windows app with:

```powershell
.\scripts\quality-packaging.ps1
```

Compile the D-drive Inno Setup installer after the portable build passes:

```powershell
.\scripts\build-windows-installer.ps1 -SkipAppBuild
```
