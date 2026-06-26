# Changelog

All notable local release-candidate changes for Aquill are tracked here.

## Unreleased

- Keep the project source-available under the PolyForm Noncommercial License 1.0.0.
- Keep generated media, transcripts, caches, databases, temp files, model files, and build artifacts under the current D-drive checkout.
- Keep release candidates gated by `scripts\release-check.ps1`.
- Keep local API/web startup and cleanup behind `scripts\start-local.ps1` and `scripts\stop-local.ps1`.
- Add `scripts\doctor.ps1` for one-command local environment checks.
- Make PowerShell helper scripts resolve the current D-drive checkout instead of a single machine path.
- Add public-alpha README polish and security/privacy guidance.
- Harden cancellation-state backend tests against valid fast-worker timing.
- Add public contact details for collaboration, product, and licensing enquiries.

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
