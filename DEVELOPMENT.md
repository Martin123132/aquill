# Development Checklist

Use this checklist before and after local changes.

## Storage Rules

- Keep project work under `D:\revenge-tour\transcriber`.
- Do not create project media, outputs, archives, screenshots, traces, caches, databases, model files, or build artifacts on `C:\`.
- Run project scripts through `D:\revenge-tour\transcriber\scripts\dev-env.ps1` or one of the wrapper scripts that imports it.
- Do not bypass the D-drive checks in `app\src\revenge_transcriber\paths.py`.

## Local Setup

```powershell
D:\revenge-tour\transcriber\scripts\setup.ps1
D:\revenge-tour\transcriber\scripts\setup-web.ps1
```

Start local services when needed:

```powershell
D:\revenge-tour\transcriber\scripts\serve-api.ps1 --host 127.0.0.1 --port 8091
D:\revenge-tour\transcriber\scripts\serve-web.ps1
```

## Quality Gates

Run the default local gate before committing:

```powershell
D:\revenge-tour\transcriber\scripts\quality-all.ps1
```

When API and web servers are already running, add the web smoke:

```powershell
D:\revenge-tour\transcriber\scripts\quality-all.ps1 -IncludeWebSmoke
```

When the API is running and at least one completed local job exists, add archive smoke:

```powershell
D:\revenge-tour\transcriber\scripts\quality-all.ps1 -IncludeArchiveSmoke
```

## Git Hygiene

- Commit source, docs, package manifests, and scripts.
- Do not commit `inputs/`, `outputs/`, `data/`, `models/`, `cache/`, `tmp/`, `.venv/`, `web/node_modules/`, `web/dist/`, or `web/tsconfig.tsbuildinfo`.
- Check staged files before each commit:

```powershell
git -C D:\revenge-tour\transcriber status --short
git -C D:\revenge-tour\transcriber diff --cached --stat
```

- Do not push unless a safe remote is configured and the user has authorized publishing from this thread.

## License Posture

- This project is source-available under the PolyForm Noncommercial License 1.0.0.
- Do not call it OSI open source in docs, package metadata, releases, or public descriptions.
- Keep the commercial-use boundary intact: no paid subscription wrapping, hosted transcription/conversion service use, resale, or commercial SaaS inclusion without a separate commercial license.

## Privacy

- Keep transcription local-first.
- Do not upload user media, transcripts, archives, private URLs, credentials, databases, screenshots, or generated outputs to cloud services.
- Public proof material, if created later, must be sanitized and must not include private media, transcripts, internal paths beyond the documented D-drive project root, credentials, or business-sensitive details.
