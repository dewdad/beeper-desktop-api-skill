#!/usr/bin/env python3
"""
Re-runnable verification of the watcher's matches() logic WITHOUT a live socket
or an inbound message. Point it at the deployed watcher.py:

    <automation-dir>/.venv/bin/python test_matches.py <automation-dir>/watcher.py

or, if run with no argument, it defaults to ~/.beeper-automation/watcher.py.

Exits non-zero if any case fails. Run this after editing matches() / the
vip.json semantics, or to prove the alert brain before enabling the watcher.
"""
import importlib.util
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    os.path.join(os.environ.get("BEEPER_AUTOMATION_DIR", "~/.beeper-automation"), "watcher.py")
)
path = os.path.expanduser(path)
spec = importlib.util.spec_from_file_location("w", path)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

cfg = {
    "alert_all_dms": True,
    "vip_senders": ["mor parag"],
    "vip_keywords": ["דחוף", "urgent"],
    "mute_networks": ["linkedin"],
    "mute_chats": ["!noisy:beeper.local"],
}
cases = [
    ("self message (NO alert)",  {"isSender": True, "senderName": "Me", "text": "hi"}, None, False),
    ("VIP sender in group",      {"senderName": "Mor Parag", "text": "yo", "network": "WhatsApp"}, "group", True),
    ("keyword hebrew in group",  {"senderName": "Rando", "text": "זה דחוף מאוד", "network": "Telegram"}, "group", True),
    ("keyword english",          {"senderName": "Rando", "text": "this is URGENT", "network": "Telegram"}, "group", True),
    ("plain 1:1 DM",             {"senderName": "Doralon", "text": "hey", "network": "Google Messages"}, "single", True),
    ("plain group no match",     {"senderName": "Rando", "text": "lol", "network": "WhatsApp"}, "group", False),
    ("muted network DM",         {"senderName": "Recruiter", "text": "job?", "network": "LinkedIn"}, "single", False),
    ("muted chat VIP",           {"senderName": "Mor Parag", "text": "x", "network": "WhatsApp", "chatID": "!noisy:beeper.local"}, "group", False),
]
ok = True
for name, entry, ctype, expect in cases:
    hit, reason = w.matches(entry, cfg, ctype)
    good = (hit == expect)
    ok = ok and good
    print(f"{'✓' if good else '✗ FAIL'}  {name:28s} -> alert={hit} ({reason or '-'})")
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
