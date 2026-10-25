#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Console helpers that keep the CLI readable on Windows terminals.

Two independent problems are solved here.

**1. The code page.** A Chinese Windows console uses cp936 (GBK) by default.
When stdout is a pipe (an agent capturing the output) or a file, Python
encodes the text with the locale encoding instead of UTF-8. Any character
outside that code page then raises ``UnicodeEncodeError`` and kills the
command — this is exactly how ``--check-note`` died on ``print("\\n\\U0001f4dd ...")``.
``configure_stdio()`` forces UTF-8 with a replacement fallback, so the output
survives and stays readable by any tool that assumes UTF-8.

**2. Decorative symbols.** Emoji are not encodable in most legacy code pages
and add nothing to a log an agent has to parse. The console uses the plain
ASCII markers below instead. Unicode stays inside the files we write, where it
is always written with an explicit ``encoding="utf-8"``.
"""

import io
import os
import platform
import shutil
import sys

# ASCII-only console markers. Do not replace these with emoji: the whole
# point is that every character printed to a console survives a legacy
# Windows code page.
OK = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"
ARROW = "->"
NOTE = ">>"

_UTF8_ALIASES = {"utf8", "utf_8", "u8", "utf"}


def _is_utf8(stream) -> bool:
    encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
    return encoding in _UTF8_ALIASES


def configure_stdio() -> bool:
    """Force UTF-8 on stdout/stderr.

    Returns True when at least one stream was reconfigured. Safe to call
    more than once and safe to call when the streams are captured by a test
    runner (streams without ``reconfigure`` are skipped).
    """
    changed = False
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            # pythonw.exe on Windows has no stdout at all.
            continue
        if _is_utf8(stream):
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
            changed = True
        except (ValueError, OSError, AttributeError, io.UnsupportedOperation):
            continue
    return changed


def store_alias_launchers() -> list:
    """Return the Windows Store alias stubs found on PATH.

    ``python`` / ``python3`` on a fresh Windows install resolve to
    ``%LOCALAPPDATA%\\Microsoft\\WindowsApps\\python3.exe``, a zero-byte
    reparse point that exits with code 49 and prints nothing. Detecting it
    turns a mysterious "exit code 49" into an actionable message.
    """
    if platform.system() != "Windows":
        return []
    found = []
    for name in ("python3", "python"):
        path = shutil.which(name)
        if not path:
            continue
        normalised = os.path.normpath(path).lower()
        if "microsoft\\windowsapps" in normalised:
            found.append({"name": name, "path": path})
    return found


def interpreter_is_store_alias() -> bool:
    """True when the running interpreter lives in the WindowsApps folder."""
    if platform.system() != "Windows":
        return False
    executable = os.path.normpath(sys.executable or "").lower()
    return "microsoft\\windowsapps" in executable
