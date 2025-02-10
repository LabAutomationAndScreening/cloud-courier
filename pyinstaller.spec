#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- mode: python -*-

# the shebang identifies this file as a 'python' 'type' for pre-commit hooks

import inspect
import os
import sys

# https://stackoverflow.com/questions/37319911/python-how-to-specify-output-folders-in-pyinstaller-spec-file?rq=1

use_upx = True

block_cipher = None
sys.modules["FixTk"] = None


a = Analysis(
    [os.path.join("src", "entrypoint.py")],
    pathex=["dist"],
    binaries=[],
    data=[],
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
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

print("Modules/packages found during analysis:")  # allow-print
for this_info in sorted(a.pure, key=lambda x: x[0]):
    print(this_info)  # allow-print


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
coll = COLLECT(  # type: ignore # noqa: F821   the 'COLLECT' object is special to how pyinstaller reads the file
    exe,
    a.binaries,
    a.zipfiles,
    a.data,
    strip=False,
    upx=use_upx,
    upx_exclude=[
        "vcruntime140.dll",  # UPX breaks this dll  https://github.com/pyinstaller/pyinstaller/pull/3821
        "qwindows.dll",  # UPX also has trouble with PyQt https://github.com/upx/upx/issues/107
    ],
    name="cloud-courier",
)
