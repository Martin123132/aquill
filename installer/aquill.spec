from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata


project_root = Path(SPECPATH).parent

datas = [
    (str(project_root / "web" / "dist"), "web/dist"),
    (str(project_root / "LICENSE"), "."),
    (str(project_root / "COMMERCIAL_USE.md"), "."),
    (str(project_root / "CONTACT.md"), "."),
    (str(project_root / "SECURITY.md"), "."),
]
binaries = []
hiddenimports = [
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
]

for package in (
    "ctranslate2",
    "faster_whisper",
    "tokenizers",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

for distribution in ("faster-whisper", "imageio-ffmpeg", "pywebview"):
    datas += copy_metadata(distribution)

a = Analysis(
    [str(project_root / "installer" / "aquill-desktop.py")],
    pathex=[str(project_root / "app" / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "cefpython3",
        "gi",
        "httptools",
        "tkinter",
        "uvloop",
        "watchfiles",
        "websockets",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Aquill",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(project_root / "installer" / "aquill-version.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Aquill",
)
