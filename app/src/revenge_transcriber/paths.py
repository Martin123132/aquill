from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ROOT = Path(os.environ.get("TRANSCRIBER_ROOT", r"D:\revenge-tour\transcriber"))


class StoragePolicyError(RuntimeError):
    """Raised when a write target violates the D-drive storage policy."""


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def require_d_drive(path: str | Path, label: str) -> Path:
    resolved = resolve_path(path)
    drive = resolved.drive.upper()
    if drive != "D:":
        raise StoragePolicyError(f"{label} must be on D:, got {resolved}")
    return resolved


def project_root() -> Path:
    return require_d_drive(DEFAULT_ROOT, "Project root")


def models_dir() -> Path:
    return project_root() / "models"


def outputs_dir() -> Path:
    return project_root() / "outputs"


def inputs_dir() -> Path:
    return project_root() / "inputs"


def tmp_dir() -> Path:
    return project_root() / "tmp"


def cache_dir() -> Path:
    return project_root() / "cache"


def data_dir() -> Path:
    return project_root() / "data"


def ensure_project_dirs() -> None:
    for path in (
        project_root(),
        models_dir(),
        inputs_dir(),
        outputs_dir(),
        tmp_dir(),
        cache_dir(),
        data_dir(),
        cache_dir() / "pip",
        cache_dir() / "huggingface",
        cache_dir() / "torch",
        cache_dir() / "pycache",
    ):
        path.mkdir(parents=True, exist_ok=True)


def configure_environment() -> None:
    ensure_project_dirs()
    env_defaults = {
        "TRANSCRIBER_ROOT": str(project_root()),
        "TEMP": str(tmp_dir()),
        "TMP": str(tmp_dir()),
        "PIP_CACHE_DIR": str(cache_dir() / "pip"),
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "HF_HOME": str(cache_dir() / "huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(cache_dir() / "huggingface" / "hub"),
        "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
        "TRANSFORMERS_CACHE": str(cache_dir() / "huggingface" / "transformers"),
        "TORCH_HOME": str(cache_dir() / "torch"),
        "XDG_CACHE_HOME": str(cache_dir()),
        "PYTHONPYCACHEPREFIX": str(cache_dir() / "pycache"),
        "UV_CACHE_DIR": str(cache_dir() / "uv"),
    }
    for key, value in env_defaults.items():
        os.environ[key] = value


def require_output_dir(path: str | Path | None) -> Path:
    output = outputs_dir() if path is None else require_d_drive(path, "Output directory")
    output.mkdir(parents=True, exist_ok=True)
    return output
