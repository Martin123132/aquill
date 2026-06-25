# Aquill

Source-available, local-first transcription and subtitle generation.

The first goal is simple: replace paid casual transcription workflows with a tool that runs locally, keeps user media private, and exports useful files without subscriptions, watermarks, or credits.

## License

Aquill is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).

It is free for personal, hobby, research, testing, educational, charitable, public-interest, and other noncommercial local use. Commercial hosting, resale, paid subscription use, ad-supported service use, or inclusion in a paid transcription, subtitle, file conversion, or media automation service is not permitted without a separate commercial license.

See [COMMERCIAL_USE.md](COMMERCIAL_USE.md) for the plain-English policy.

## Contact

For collaboration, information on existing products, commercial licensing, or other enquiries, see [CONTACT.md](CONTACT.md).

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

Start the local API and web UI together:

```powershell
D:\revenge-tour\transcriber\scripts\start-local.ps1
```

Open:

```text
http://127.0.0.1:5190/
```

Stop both local servers:

```powershell
D:\revenge-tour\transcriber\scripts\stop-local.ps1
```

The lower-level API and web wrappers are still available for separate debugging:

```powershell
D:\revenge-tour\transcriber\scripts\serve-api.ps1 --host 127.0.0.1 --port 8091
D:\revenge-tour\transcriber\scripts\serve-web.ps1
```

Default URLs:

```text
http://127.0.0.1:8091/api/health
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

## Release Posture Check

Before tagging, sharing, or publishing a local build, run:

```powershell
D:\revenge-tour\transcriber\scripts\release-check.ps1
```

This runs the default quality checks, confirms the PolyForm Noncommercial license files and package metadata are intact, checks that the app still shows the noncommercial license boundary, and audits executable source paths for accidental `C:\` usage.

Release-candidate notes are tracked in [CHANGELOG.md](CHANGELOG.md).

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
18. Preview archive metadata before importing restored jobs.
19. Show the PolyForm Noncommercial license boundary in the local UI and verify release posture with one D-drive-safe script.
20. Start and stop the local API/web pair with D-drive-safe wrapper scripts and logs.
