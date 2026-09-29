#!/usr/bin/env python3

# the shebang identifies this file as a 'python' 'type' for pre-commit hooks

import sys
import sysconfig
from pathlib import Path

from fastapi_offline.core import _STATIC_PATH


# https://stackoverflow.com/questions/37319911/python-how-to-specify-output-folders-in-pyinstaller-spec-file?rq=1

use_upx = False
include_windows_service = True

block_cipher = None
sys.modules["FixTk"] = None

_extra_binaries: set[tuple[str, str]] = set()
_extra_hiddenimports: set[str] = set()

if include_windows_service and sys.platform == "win32":
    # pywintypes/pythoncom DLLs live in pywin32_system32, a sibling of win32/ inside site-packages.
    # uv may skip pywin32's post-install .pth processing, so importlib.find_spec("win32service")
    # returns None — resolve via sysconfig.purelib instead, which is independent of sys.path.
    _pywin32_system32 = Path(sysconfig.get_path("purelib")) / "pywin32_system32"
    if not _pywin32_system32.is_dir():
        raise RuntimeError(f"pywin32_system32 not found at {_pywin32_system32}; is pywin32 installed?")
    for _dll in sorted(_pywin32_system32.glob("*.dll")):
        _extra_binaries.add((str(_dll), "."))

    # servicemanager/win32service imports are inside a function body so static analysis misses them.
    _extra_hiddenimports |= {
        "servicemanager",
        "win32service",
        "win32serviceutil",
        "win32event",
        "win32con",
        "win32timezone",
        "pywintypes",
    }


a = Analysis(
    [Path("src") / "entrypoint.py"],
    pathex=["dist"],
    binaries=sorted(_extra_binaries),
    datas=[  # spellchecker:disable-line
        (Path("src") / "static", Path("static")),
        (_STATIC_PATH, "fastapi_offline/static"),
    ],
    hiddenimports=[
        "eventlet.hubs.epolls",
        "eventlet.hubs.kqueue",
        "eventlet.hubs.selects",
        "dns",
        "dns.asyncquery",
        "dns.asyncresolver",
        "dns.dnssec",
        "dns.e164",
        "dns.hash",
        "dns.namedict",
        "dns.tsigkeyring",
        "dns.update",
        "dns.version",
        "dns.versioned",
        "dns.zone",
        "engineio.async_drivers.eventlet",
        *sorted(_extra_hiddenimports),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

print("Modules/packages found during analysis:")
for this_info in sorted(a.pure, key=lambda x: x[0]):
    print(this_info)


pyz = PYZ(  # type: ignore # noqa: F821   the 'PYZ' object is special to how pyinstaller reads the file
    a.pure, a.zipped_data, cipher=block_cipher
)
exe = EXE(  # type: ignore # noqa: F821   the 'EXE' object is special to how pyinstaller reads the file
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="cloud-courier",
    debug=False,
    strip=False,
    upx=use_upx,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas, # spellchecker:disable-line
    strip=False,
    upx=use_upx,
    upx_exclude=[
        "vcruntime140.dll",  # UPX breaks this dll  https://github.com/pyinstaller/pyinstaller/pull/3821
        "qwindows.dll",  # UPX also has trouble with PyQt https://github.com/upx/upx/issues/107
    ],
    name="cloud-courier",
)

# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
