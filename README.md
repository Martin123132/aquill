# Revenge Transcriber

Open-source, local-first transcription and subtitle generation.

The first goal is simple: replace paid casual transcription workflows with a tool that runs locally, keeps user media private, and exports useful files without subscriptions, watermarks, or credits.

## Hard Storage Rule

This project is configured for `D:\revenge-tour\transcriber`.

Generated files, model downloads, temp files, caches, test inputs, and outputs should stay on `D:\`.

Supervisor, delegation, or helper-agent instructions do not override this rule. Do not create project artifacts on `C:\`; this laptop's C drive is not project storage.

## Quick Start

Set up the backend CLI/API:

```powershell
D:\revenge-tour\transcriber\scripts\setup.ps1
```

Put local media under `D:\revenge-tour\transcriber\inputs`, then run:

```powershell
D:\revenge-tour\transcriber\scripts\transcribe.ps1 D:\revenge-tour\transcriber\inputs\sample.mp4 --model tiny --language en
```

The CLI writes a timestamped job folder under:

```text
D:\revenge-tour\transcriber\outputs
```

Each job produces:

- `transcript.txt`
- `transcript.json`
- `subtitles.srt`
- `subtitles.vtt`

## Local Web App

Install web dependencies:

```powershell
D:\revenge-tour\transcriber\scripts\setup-web.ps1
```

Start the API:

```powershell
D:\revenge-tour\transcriber\scripts\serve-api.ps1 --host 127.0.0.1 --port 8091
```

Start the web UI:

```powershell
D:\revenge-tour\transcriber\scripts\serve-web.ps1
```

Open:

```text
http://127.0.0.1:5190/
```

Completed jobs can be exported from the active job actions. ZIP archives can be imported from the intake panel and are restored as completed local jobs.

## Backend Quality Check

Run the compile checks and fake-driven backend tests with:

```powershell
D:\revenge-tour\transcriber\scripts\quality-backend.ps1
```

## Web Quality Check

After `setup-web.ps1`, run the TypeScript and Vite production build check with:

```powershell
D:\revenge-tour\transcriber\scripts\quality-web.ps1
```

This creates ignored build artifacts under `D:\revenge-tour\transcriber\web\dist`.

## Full Local Quality Check

Run backend and web quality checks together with:

```powershell
D:\revenge-tour\transcriber\scripts\quality-all.ps1
```

To also verify the live archive export/import round-trip, start the API first, ensure at least one completed local job exists, then run:

```powershell
D:\revenge-tour\transcriber\scripts\quality-all.ps1 -IncludeArchiveSmoke
```

To verify the running web UI can reach the API and exposes the storage/archive controls, start both servers, then run:

```powershell
D:\revenge-tour\transcriber\scripts\quality-all.ps1 -IncludeWebSmoke
```

## Archive Smoke Check

With the API running and at least one completed local job available, verify the export/import API round-trip with:

```powershell
D:\revenge-tour\transcriber\scripts\smoke-archive-roundtrip.ps1
```

The smoke check exports a completed job archive, imports it through `POST /api/jobs/import`, confirms the restored job exposes artifacts, then deletes only the imported smoke job.

## Local Artifacts

The following directories are intentionally ignored and may contain private or large local data:

- `inputs/` uploaded or manually staged source media
- `outputs/` generated transcripts, subtitles, optional extracted WAV files, and rescanned job folders
- `data/` SQLite job history
- `models/` local Whisper model downloads
- `cache/` pip, npm, Hugging Face, Torch, Python, and tooling caches
- `tmp/` temporary extraction and test files
- `web/dist/` and `web/tsconfig.tsbuildinfo` web build output

Do not commit media, transcripts, model files, caches, databases, or build output unless a future release process explicitly calls for a sanitized fixture.

## Project Layout

```text
app/       Python package and CLI
web/       React/Vite browser UI
scripts/   PowerShell setup and run helpers
models/    Whisper model downloads, ignored by Git
inputs/    Local media inputs, ignored by Git
outputs/   Generated transcripts/subtitles, ignored by Git
tmp/       Temporary media files, ignored by Git
cache/     Tooling and ML caches, ignored by Git
data/      SQLite job history, ignored by Git
```

## Current Status

The first vertical slice works:

1. Extract audio with FFmpeg.
2. Transcribe locally with `faster-whisper`.
3. Export TXT, JSON, SRT, and VTT.
4. Keep generated project data on `D:\`.
5. Run jobs through a local FastAPI server and React workbench.
6. Persist job history in SQLite and reload it after API restarts.
7. Edit transcript segments and regenerate TXT, JSON, SRT, and VTT.
8. Queue multiple files from the UI and process them sequentially.
9. Retry, cancel queued or running jobs, delete, and open output folders.
10. Inspect local Whisper model downloads and disk usage.
11. Track progress messages, start time, and completion time for jobs.
12. Export completed jobs as ZIP archives with manifest and available artifacts.
13. Import validated job archives back into local D-drive storage as restored completed jobs.
14. Smoke-test archive export/import round-trips against the running local API.
15. Run backend, web, and optional live archive smoke checks from one D-drive-safe quality command.
16. Show active D-drive project, input, output, model, data, temp, and cache paths in the local UI.
17. Smoke-test the running web UI and API proxy without adding browser test dependencies.
