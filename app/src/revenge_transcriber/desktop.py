from __future__ import annotations

import argparse
import ctypes
import importlib
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .paths import cache_dir, configure_environment, installed_data_root, set_project_root, tmp_dir


class DesktopStartupError(RuntimeError):
    """Raised when the local desktop runtime cannot start safely."""


def close_windows_handle(handle: int) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (ctypes.c_void_p,)
    close_handle.restype = ctypes.c_bool
    close_handle(ctypes.c_void_p(handle))


@dataclass
class SingleInstanceLock:
    handle: int | None = None

    @classmethod
    def acquire(cls) -> SingleInstanceLock:
        if sys.platform != "win32":
            return cls()

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        create_mutex.restype = ctypes.c_void_p
        handle = create_mutex(None, False, "Local\\TwoHandsNetwork.Aquill")
        if not handle:
            raise DesktopStartupError("Aquill could not create its single-instance lock.")
        if ctypes.get_last_error() == 183:
            close_windows_handle(int(handle))
            raise DesktopStartupError("Aquill is already running.")
        return cls(handle=int(handle))

    def close(self) -> None:
        if self.handle is None or sys.platform != "win32":
            return
        close_windows_handle(self.handle)
        self.handle = None


@dataclass
class LocalServerRuntime:
    server: Any
    thread: threading.Thread
    listener: socket.socket
    url: str

    def stop(self, timeout: float = 10) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=timeout)
        if self.thread.is_alive():
            self.server.force_exit = True
            self.thread.join(timeout=2)
        try:
            self.listener.close()
        except OSError:
            pass


def start_local_server(
    application: Any,
    host: str = "127.0.0.1",
    port: int = 0,
    timeout: float = 30,
) -> LocalServerRuntime:
    import uvicorn

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(2048)
    selected_port = int(listener.getsockname()[1])
    url = f"http://{host}:{selected_port}"

    config = uvicorn.Config(
        application,
        host=host,
        port=selected_port,
        loop="asyncio",
        http="h11",
        ws="none",
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(
        target=server.run,
        kwargs={"sockets": [listener]},
        name="aquill-local-api",
        daemon=True,
    )
    runtime = LocalServerRuntime(server=server, thread=thread, listener=listener, url=url)
    thread.start()
    try:
        wait_for_health(f"{url}/api/health", thread, timeout)
    except Exception:
        runtime.stop()
        raise
    return runtime


def wait_for_health(uri: str, thread: threading.Thread, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not thread.is_alive():
            raise DesktopStartupError("Aquill's local service stopped during startup.")
        try:
            with urllib.request.urlopen(uri, timeout=1) as response:  # noqa: S310 - fixed loopback URL.
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise DesktopStartupError("Timed out while starting Aquill's local service.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Aquill")
    parser.add_argument("--data-root", type=Path, help="Writable D-drive folder for Aquill data.")
    parser.add_argument("--port", type=int, default=0, help="Loopback port. Zero selects a free port.")
    parser.add_argument("--debug", action="store_true", help="Enable WebView debugging tools.")
    parser.add_argument("--headless-smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"Aquill {__version__}")
    return parser


def verify_packaged_runtime() -> None:
    import imageio_ffmpeg

    importlib.import_module("faster_whisper")
    importlib.import_module("webview")
    importlib.import_module("webview.platforms.winforms")
    importlib.import_module("webview.platforms.edgechromium")
    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    if not ffmpeg.is_file():
        raise DesktopStartupError("Aquill's bundled FFmpeg executable is missing.")


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instance_lock = SingleInstanceLock.acquire()
    try:
        data_root = args.data_root or installed_data_root()
        set_project_root(data_root)
        configure_environment()

        from . import server as api_server

        if not api_server.WEB_APP_MOUNTED:
            raise DesktopStartupError("Aquill's bundled interface is missing.")

        runtime = start_local_server(api_server.app, port=args.port)
        try:
            if args.headless_smoke:
                verify_packaged_runtime()
                return 0

            try:
                import webview
            except ImportError as exc:
                raise DesktopStartupError("The Aquill desktop window dependency is not installed.") from exc

            webview.create_window(
                "Aquill",
                runtime.url,
                width=1280,
                height=820,
                min_size=(780, 560),
                background_color="#f7f8f8",
                text_select=True,
            )
            webview.start(
                gui="edgechromium",
                debug=args.debug,
                private_mode=False,
                storage_path=str(cache_dir() / "webview"),
            )
            return 0
        finally:
            runtime.stop()
    finally:
        instance_lock.close()


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except Exception as exc:  # noqa: BLE001 - packaged startup failures must be visible.
        message = f"Aquill could not start.\n\n{exc}"
        try:
            tmp_dir().mkdir(parents=True, exist_ok=True)
            (tmp_dir() / "desktop-startup-error.log").write_text(message + "\n", encoding="utf-8")
        except Exception:
            pass
        if "--headless-smoke" not in (argv if argv is not None else sys.argv[1:]):
            show_error_dialog(message)
        print(message, file=sys.stderr)
        return 1


def show_error_dialog(message: str) -> None:
    if sys.platform != "win32":
        return
    ctypes.windll.user32.MessageBoxW(0, message, "Aquill", 0x10)  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
