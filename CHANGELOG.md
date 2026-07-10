# Changelog

All notable local release-candidate changes for Aquill are tracked here.

## Unreleased

### Added

- Serve the compiled React workbench and FastAPI API from one local process at `http://127.0.0.1:5190`.
- Keep the Vite/API two-process workflow available through `scripts\start-dev.ps1` for development.
- Recover queued or running jobs during API startup, remove abandoned temporary WAV files, and preserve original inputs for retry.
- Add focused Vitest/Testing Library coverage for transcript and lyrics editing, archive import, interrupted-job retry, and upload errors.
- Add transcript segment split/merge, editable start/end times, find/replace, and grouped undo/redo controls.
- Extend transcript saves to validate and persist structural timing edits while retaining text-only API compatibility.

### Changed

- Make `scripts\start-local.ps1` build the production interface, start one hidden local service, and open the app by default.
- Make `scripts\quality-web.ps1` run frontend tests before the production build.
- Make the live UI smoke inspect the compiled bundle and same-origin API rather than Vite source files.

### Verified

- Backend quality passes with 26 fake-driven tests.
- Frontend quality passes with 5 component workflow tests and a production build.
- The compiled UI and API pass the live smoke from the same port with all runtime storage under the D-drive checkout.
- Desktop and narrow-viewport in-app browser checks pass with no console warnings or errors.

## 0.1.0-alpha - 2026-06-29

### Added

- Keep the project source-available under the PolyForm Noncommercial License 1.0.0.
- Keep generated media, transcripts, caches, databases, temp files, model files, and build artifacts under the current D-drive checkout.
- Keep release candidates gated by `scripts\release-check.ps1`.
- Keep local API/web startup and cleanup behind `scripts\start-local.ps1` and `scripts\stop-local.ps1`.
- Add `scripts\doctor.ps1` for one-command local environment checks.
- Make PowerShell helper scripts resolve the current D-drive checkout instead of a single machine path.
- Add public-alpha README polish and security/privacy guidance.
- Add lyrics preview/apply/restore for completed song jobs with one-time original artifact backups.
- Add a Song preset for music-oriented local transcription defaults.
- Harden cancellation-state backend tests against valid fast-worker timing.
- Add public contact details for collaboration, product, and licensing enquiries.

### Verified

- `scripts\release-check.ps1` passes with backend tests and web build.
- `scripts\quality-all.ps1 -IncludeWebSmoke` passes against the running local API and web UI.

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
- One-command local API/web start and stop scripts with logs under the D-drive checkout `tmp` directory.

### Verified

- `scripts\quality-all.ps1 -IncludeWebSmoke` runs backend tests, web build, and live API/UI smoke checks.
- `scripts\release-check.ps1` verifies quality, license metadata, UI license copy, old wording, and D-drive posture.
