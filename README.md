# Aquill

Local transcription without subscriptions.

Aquill is a source-available, local-first transcription and subtitle workbench. It is built for people who want to transcribe audio or video on their own machine, keep media private, and export useful files without credits, watermarks, or subscription gates.

## What It Does

- Runs the compiled React workbench and FastAPI backend in one local process.
- Runs as a native Windows desktop window with its local service contained inside the app lifecycle.
- Queues audio or video files for local transcription with `faster-whisper`.
- Exports TXT, JSON, SRT, and VTT.
- Lets you edit text and timing, split or merge segments, find/replace, undo/redo, and regenerate exports.
- Flags long lines, excessive reading speed, and short or long subtitle cues against adjustable local thresholds.
- Wraps subtitle cue text at an adjustable line length with normal undo/redo before saving regenerated exports.
- Plays validated local job media in the editor and highlights the cue at the current playback time.
- Previews and applies pasted known lyrics into timed transcript and subtitle exports.
- Backs up rough song transcripts before lyrics alignment so originals can be restored.
- Offers a Song preset with safer defaults for music transcription.
- Shows local model, storage, progress, and job state.
- Exports completed jobs as ZIP archives.
- Previews and imports Aquill job archives back into local storage.
- Keeps media, transcripts, databases, models, temp files, and caches on `D:\`.

## Not Yet

- No code-signed stable Windows release yet.
- No cloud transcription or hosted SaaS mode.
- No speaker diarization UI yet.
- No stable release yet.
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

`start-local.ps1` builds the interface, starts Aquill, and opens the address in the default browser. Pass `-NoBrowser` when you only want to start the process.

Stop Aquill:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-local.ps1
```

## Windows App

Install the desktop packaging dependencies into Aquill's D-drive virtual environment, then launch the native development app:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-packaging.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-desktop.ps1
```

Closing the Aquill window also stops its private loopback service. Installed builds keep all writable application data under `D:\Aquill`; the application itself installs to `D:\Apps\Aquill`.

Build the portable app, verify its packaged runtime, and create the Windows installer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows-app.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\quality-packaging.ps1 -SkipBuild
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1 -SkipAppBuild
```

Generated portable ZIPs, installers, SHA-256 hashes, and release metadata are written to the ignored `release\` directory. The store-neutral seed metadata is [installer/app-store-manifest.template.json](installer/app-store-manifest.template.json). Development installers are unsigned, so Windows may show an unknown-publisher warning until a future release is code-signed.

For frontend development with Vite hot reload and the API on port `8091`, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
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

Build and smoke-test the native packaged application without opening a window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\quality-all.ps1 -IncludePackaging
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
- `app/build/`, `app/dist/`, and `release/` packaged application and installer output

Do not commit media, transcripts, model files, caches, databases, screenshots, archives, or build output unless a future release process explicitly calls for sanitized fixtures.

## Project Layout

```text
app/       Python package and CLI
web/       React/Vite browser UI
scripts/   PowerShell setup, quality, smoke, and run helpers
installer/ Windows executable, installer, and app-store build definitions
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
8. Preview pasted known lyrics, apply them to rough song transcriptions, and regenerate timed TXT, JSON, SRT, and VTT.
9. Back up original transcript/subtitle artifacts before lyrics alignment and restore them from the UI.
10. Use a Song preset that defaults to `small`, English, local transcription, voice filtering, and int8 compute.
11. Queue multiple files from the UI and process them sequentially.
12. Retry, cancel queued or running jobs, delete, and open output folders.
13. Inspect local Whisper model downloads and disk usage.
14. Track progress messages, start time, and completion time for jobs.
15. Export completed jobs as ZIP archives with manifest and available artifacts.
16. Import validated job archives back into local D-drive storage as restored completed jobs.
17. Smoke-test archive export/import round-trips against the running local API.
18. Run backend, web, release posture, doctor, and optional live smoke checks from D-drive-safe scripts.
19. Show active D-drive project, input, output, model, data, temp, and cache paths in the local UI.
20. Preview archive metadata before importing restored jobs.
21. Show the PolyForm Noncommercial license boundary in the local UI.
22. Serve the compiled workbench and API from one local process on port `5190`.
23. Recover interrupted jobs after an app restart, clean their abandoned temporary audio, and leave them ready to retry.
24. Run automated browser-component tests for uploads, retries, transcript/lyrics editing, and archive import.
25. Split and merge transcript cues, edit start/end times, find and replace text, and undo or redo local edits before saving regenerated exports.
26. Review per-cue line length, line count, reading speed, and duration warnings with adjustable quality thresholds.
27. Wrap cue text without losing words, then save the wrapped text into regenerated SRT and VTT exports.
28. Preview retained audio or the original validated local upload and follow the active cue during playback.
29. Run as a single-instance native Windows app whose private loopback service stops with its window.
30. Build a portable x64 application, D-drive installer, SHA-256 release metadata, and app-store manifest seed.
