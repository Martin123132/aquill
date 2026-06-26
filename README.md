# Aquill

Local transcription without subscriptions.

Aquill is a source-available, local-first transcription and subtitle workbench. It is built for people who want to transcribe audio or video on their own machine, keep media private, and export useful files without credits, watermarks, or subscription gates.

## What It Does

- Runs a local FastAPI backend and React/Vite workbench.
- Queues audio or video files for local transcription with `faster-whisper`.
- Exports TXT, JSON, SRT, and VTT.
- Lets you edit transcript segments and regenerate exports.
- Shows local model, storage, progress, and job state.
- Exports completed jobs as ZIP archives.
- Previews and imports Aquill job archives back into local storage.
- Keeps media, transcripts, databases, models, temp files, and caches on `D:\`.

## Not Yet

- No packaged installer yet.
- No cloud transcription or hosted SaaS mode.
- No speaker diarization UI yet.
- No full release tag yet.
- No promise that huge media jobs are laptop-light.

## License

Aquill is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).

It is free for personal, hobby, research, testing, educational, charitable, public-interest, and other noncommercial local use. Commercial hosting, resale, paid subscription use, ad-supported service use, or inclusion in a paid transcription, subtitle, file conversion, or media automation service is not permitted without a separate commercial license.

See [COMMERCIAL_USE.md](COMMERCIAL_USE.md) for the plain-English policy.

## Contact

For collaboration, information on existing products, commercial licensing, or other enquiries, see [CONTACT.md](CONTACT.md).

## Security And Privacy

Aquill is local-first by design. Keep private media, transcripts, databases, archives, screenshots, and generated outputs out of public repos and cloud services. See [SECURITY.md](SECURITY.md) for reporting and privacy guidance.

## Storage Rule

Aquill is designed for a D-drive checkout. Clone it somewhere on `D:\`, for example:

```powershell
git clone https://github.com/Martin123132/aquill.git D:\Projects\aquill
cd D:\Projects\aquill
```

The scripts resolve the project root from their own location, then pin generated media, transcripts, databases, model downloads, caches, and temp files under that D-drive checkout. Do not use this project from a small system drive.

## Quick Start

From your D-drive Aquill checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-web.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Open:

```text
http://127.0.0.1:5190/
```

Stop both local servers:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-local.ps1
```

## CLI Use

Put local media under `inputs\`, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\transcribe.ps1 .\inputs\sample.mp4 --model tiny --language en
```

Each job writes a timestamped output folder under `outputs\` with:

- `transcript.txt`
- `transcript.json`
- `subtitles.srt`
- `subtitles.vtt`

## Quality Checks

Run the default backend and web checks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\quality-all.ps1
```

Run the live web smoke after `start-local.ps1`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\quality-all.ps1 -IncludeWebSmoke
```

Run release posture checks before tagging or sharing a local build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release-check.ps1
```

With the API running and at least one completed local job available, verify archive export/import round-trip:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-archive-roundtrip.ps1
```

Release-candidate notes are tracked in [CHANGELOG.md](CHANGELOG.md).

## Local Artifacts

The following directories are intentionally ignored and may contain private or large local data:

- `inputs/` uploaded or manually staged source media
- `outputs/` generated transcripts, subtitles, optional extracted WAV files, and rescanned job folders
- `data/` SQLite job history
- `models/` local Whisper model downloads
- `cache/` pip, npm, Hugging Face, Torch, Python, and tooling caches
- `tmp/` temporary extraction and test files
- `web/dist/` and `web/tsconfig.tsbuildinfo` web build output

Do not commit media, transcripts, model files, caches, databases, screenshots, archives, or build output unless a future release process explicitly calls for sanitized fixtures.

## Project Layout

```text
app/       Python package and CLI
web/       React/Vite browser UI
scripts/   PowerShell setup, quality, smoke, and run helpers
models/    Whisper model downloads, ignored by Git
inputs/    Local media inputs, ignored by Git
outputs/   Generated transcripts/subtitles, ignored by Git
tmp/       Temporary media files, ignored by Git
cache/     Tooling and ML caches, ignored by Git
data/      SQLite job history, ignored by Git
```

## Current Status

The first public alpha slice works:

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
15. Run backend, web, release posture, doctor, and optional live smoke checks from D-drive-safe scripts.
16. Show active D-drive project, input, output, model, data, temp, and cache paths in the local UI.
17. Preview archive metadata before importing restored jobs.
18. Show the PolyForm Noncommercial license boundary in the local UI.
