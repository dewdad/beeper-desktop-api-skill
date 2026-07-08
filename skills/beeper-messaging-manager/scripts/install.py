#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Beeper Messaging Manager installer -- entry point / version gate.
#
# This launcher is INTENTIONALLY written in the subset of syntax that parses on
# both Python 2.7 and Python 3.x (no f-strings, no type hints, no walrus). That
# matters: CPython compiles an entire module before executing any of it, so if
# the real implementation (which uses f-strings) lived here, an old interpreter
# would raise a bare SyntaxError at import time -- before any friendly message
# could print. Keeping the gate in a separate, syntax-minimal file guarantees a
# too-old interpreter gets an actionable message and a clean exit(3) instead.
#
# On Python 3.7+ this delegates to _installer_impl.py, passing through argv.
#
# Usage:
#   python3 install.py [--dir DIR] [--dry-run] [--no-schedule] [--no-supervise]
#                      [--tg-token TOKEN --tg-chat CHAT] [--force-config]
import os
import sys

_MIN = (3, 7)


def _too_old():
    found = "%d.%d.%d" % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
    sys.stderr.write(
        "\n[FAIL] The Beeper Messaging Manager installer needs Python %d.%d or "
        "newer; you have %s\n       (%s).\n" % (_MIN[0], _MIN[1], found, sys.executable)
    )
    sys.stderr.write(
        "\n       Install a modern Python 3, then re-run with it EXPLICITLY:\n"
        "         macOS:         brew install python@3.12   && python3 install.py\n"
        "         Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip && python3 install.py\n"
        "         Fedora:        sudo dnf install python3 python3-pip && python3 install.py\n"
        "         Windows:       winget install Python.Python.3.12  (then: py install.py)\n"
        "         Other:         https://www.python.org/downloads/\n"
        "\n       If several Pythons are installed, name the newest explicitly,\n"
        "       e.g.  python3.12 install.py  -- `python` alone may point at an old one.\n\n"
    )
    sys.exit(3)


def main():
    if sys.version_info[:2] < _MIN:
        _too_old()
    # Interpreter is >= 3.7: safe to import the f-string-using implementation.
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import _installer_impl
    except SyntaxError:
        # Extremely defensive: if somehow imported on an interpreter that
        # compiled the launcher but chokes on the impl, still be helpful.
        _too_old()
        return
    _installer_impl.main()


if __name__ == "__main__":
    main()
