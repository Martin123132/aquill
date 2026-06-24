# Changelog

All notable local release-candidate changes for Revenge Transcriber are tracked here.

## Unreleased

- Keep the project source-available under the PolyForm Noncommercial License 1.0.0.
- Keep generated media, transcripts, caches, databases, temp files, model files, and build artifacts under `D:\revenge-tour\transcriber`.
- Keep release candidates gated by `D:\revenge-tour\transcriber\scripts\release-check.ps1`.

## 0.1.0-local - 2026-06-24

### Added

- Local FastAPI and React/Vite transcription workbench.
- D-drive-safe project paths for inputs, outputs, data, models, caches, and temp files.
- Local job queue with retry, cancel, delete, open-output, and progress state.
- Transcript segment editing with regenerated TXT, JSON, SRT, and VTT exports.
- Archive export, preview, import, and API smoke coverage for restored jobs.
- Storage status display in the UI.
- Queue filtering and search.
- Visible UI license panel for the PolyForm Noncommercial License 1.0.0.
- Backend, web, release posture, and optional live smoke quality scripts.

### Verified

- `D:\revenge-tour\transcriber\scripts\quality-all.ps1 -IncludeWebSmoke` runs backend tests, web build, and live API/UI smoke checks.
- `D:\revenge-tour\transcriber\scripts\release-check.ps1` verifies quality, license metadata, UI license copy, old wording, and D-drive posture.
