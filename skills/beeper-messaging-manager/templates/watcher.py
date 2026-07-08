#!/usr/bin/env python3
"""
Beeper realtime alert watcher — portable, host-agnostic.

Connects to the Beeper Desktop WebSocket stream, subscribes to ALL chats, and
fires an instant alert (Telegram, or any command via ALERT_CMD) when an
INCOMING message is:
  - a 1:1 DM (when alert_all_dms is true), or
  - from a VIP sender (case-insensitive substring on senderName/senderID), or
  - contains a VIP keyword (case-insensitive substring on text; Hebrew/UTF-8 OK).

Config (vip.json) is re-read on EVERY event, so edits take effect live with no
restart. Self-sent messages (isSender=true) and muted networks/chats are ignored.
Auto-reconnects with exponential backoff. Designed to run under a supervisor
(systemd --user on Linux, launchd on macOS, or the bundled cron watchdog).

KEY NON-OBVIOUS BITS (learned the hard way — see the skill's pitfalls):
  - No domain events arrive until you send subscriptions.set {chatIDs:["*"]}
    AFTER the `ready` frame. A watcher that just connects sees the handshake
    and then silence forever.
  - Every message.upserted entry carries isSender; skip your own sends or the
    watcher alerts on the agent's own outbound messages (and you can't
    self-test by messaging yourself — it'll be filtered).
  - chat.upserted carries chat `type`; cache it to know which chats are 1:1
    (`single`) vs group, since message entries don't always carry chat type.

ENV:
  BEEPER_AUTOMATION_DIR  Base dir for vip.json / logs (default ~/.beeper-automation)
  BEEPER_WS_URL          Override WS URL (default ws://127.0.0.1:23373/v1/ws)
  BEEPER_TOKEN_FILE      Explicit path to the desktop target JSON (auto-detected otherwise)
  BEEPER_ACCESS_TOKEN    Raw bdapi_* token; overrides the target file entirely
  BEEPER_ALERT_TG_TOKEN  Telegram bot token for delivery
  BEEPER_ALERT_TG_CHAT   Telegram chat id (numeric) for delivery
  ALERT_CMD              Optional shell command to run per alert; the alert text
                         is piped to its stdin. Overrides Telegram if set.
                         e.g. ALERT_CMD='osascript -e "display notification ..."'
"""
import asyncio
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# `websockets` is only needed to actually run the daemon. Import lazily so that
# pure helpers (e.g. matches()) remain importable for unit tests on an
# interpreter that doesn't have it installed.
try:
    import websockets
except ImportError:
    websockets = None

BASE_DIR = os.path.expanduser(os.environ.get("BEEPER_AUTOMATION_DIR", "~/.beeper-automation"))
VIP_FILE = os.path.join(BASE_DIR, "vip.json")
LOG_FILE = os.path.join(BASE_DIR, "watcher.log")
WS_URL = os.environ.get("BEEPER_WS_URL", "ws://127.0.0.1:23373/v1/ws")

TG_TOKEN = os.environ.get("BEEPER_ALERT_TG_TOKEN", "")
TG_CHAT = os.environ.get("BEEPER_ALERT_TG_CHAT", "")
ALERT_CMD = os.environ.get("ALERT_CMD", "")

_seen = {}
_SEEN_TTL = 3600


def log(m):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _candidate_token_files():
    """Yield likely locations of the desktop target JSON across platforms/CLIs."""
    explicit = os.environ.get("BEEPER_TOKEN_FILE")
    if explicit:
        yield os.path.expanduser(explicit)
    home = os.path.expanduser("~")
    # @beeper/cli target file (all platforms)
    yield os.path.join(home, ".beeper", "targets", "desktop.json")
    # Windows APPDATA variant, if the CLI stored it there
    appdata = os.environ.get("APPDATA")
    if appdata:
        yield os.path.join(appdata, ".beeper", "targets", "desktop.json")


def token():
    """Resolve the bearer token: env var wins, else first readable target file."""
    if os.environ.get("BEEPER_ACCESS_TOKEN"):
        return os.environ["BEEPER_ACCESS_TOKEN"]
    for path in _candidate_token_files():
        try:
            with open(path) as f:
                tok = json.load(f).get("auth", {}).get("accessToken")
            if tok:
                return tok
        except Exception:
            continue
    raise RuntimeError(
        "No Beeper token found. Set BEEPER_ACCESS_TOKEN, or run "
        "`beeper targets add desktop desktop --port 23373` and inject a bdapi_* "
        "token (Settings -> Developers -> Approved connections)."
    )


def load_vip():
    try:
        with open(VIP_FILE) as f:
            cfg = json.load(f)
    except Exception as e:
        log(f"[warn] could not read vip.json: {e}; using safe defaults")
        cfg = {}
    return {
        "alert_all_dms": bool(cfg.get("alert_all_dms", True)),
        "vip_senders": [s.lower() for s in cfg.get("vip_senders", []) if isinstance(s, str)],
        "vip_keywords": [k.lower() for k in cfg.get("vip_keywords", []) if isinstance(k, str)],
        "mute_networks": [n.lower() for n in cfg.get("mute_networks", []) if isinstance(n, str)],
        "mute_chats": [c.lower() for c in cfg.get("mute_chats", []) if isinstance(c, str)],
    }


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def is_dm(entry, chat_type):
    return (chat_type or entry.get("chatType") or "").lower() in ("single", "dm", "direct")


def matches(entry, cfg, chat_type):
    """Return (should_alert, reason). Pure function — unit-testable, no socket."""
    if entry.get("isSender"):
        return False, None
    net = (entry.get("network") or entry.get("accountID") or "").lower()
    if any(m in net for m in cfg["mute_networks"]):
        return False, None
    cid = (entry.get("chatID") or "").lower()
    title = (entry.get("chatTitle") or "").lower()
    if any(mc in (cid, title) for mc in cfg["mute_chats"]):
        return False, None
    sender = ((entry.get("senderName") or "") + " " + (entry.get("senderID") or "")).lower()
    text = strip_html(entry.get("text") or "").lower()
    for v in cfg["vip_senders"]:
        if v and v in sender:
            return True, f"VIP sender ({entry.get('senderName') or entry.get('senderID')})"
    for k in cfg["vip_keywords"]:
        if k and k in text:
            return True, f"keyword '{k}'"
    if cfg["alert_all_dms"] and is_dm(entry, chat_type):
        return True, "direct message"
    return False, None


def notify(entry, reason):
    who = entry.get("senderName") or entry.get("senderID") or "unknown"
    net = entry.get("network") or "?"
    body = strip_html(entry.get("text") or "")
    if not body and entry.get("attachments"):
        kinds = ", ".join(a.get("type", "file") for a in entry["attachments"])
        body = f"[attachment: {kinds}]"
    msg = f"\U0001f514 Beeper alert \u00b7 {reason}\n{who} ({net}):\n{body[:800]}"
    log(f"[ALERT] {reason} | {who} ({net}): {body[:120]}")

    if ALERT_CMD:
        try:
            subprocess.run(ALERT_CMD, shell=True, input=msg.encode(), timeout=15)
        except Exception as e:
            log(f"[warn] ALERT_CMD failed: {e}")
        return
    if TG_TOKEN and TG_CHAT:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg}).encode()
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
        except Exception as e:
            log(f"[warn] telegram send failed: {e}")
    else:
        log("[warn] no delivery configured (set BEEPER_ALERT_TG_* or ALERT_CMD) — alert logged only")


def dedup(mid):
    now = time.time()
    for k in [k for k, v in _seen.items() if now - v > _SEEN_TTL]:
        _seen.pop(k, None)
    if mid in _seen:
        return True
    _seen[mid] = now
    return False


async def run_once():
    if websockets is None:
        raise RuntimeError(
            "the 'websockets' package is required to run the watcher. "
            "Install it into this interpreter: pip install websockets"
        )
    tok = token()
    chat_types = {}
    async with websockets.connect(WS_URL, additional_headers={"Authorization": f"Bearer {tok}"}) as ws:
        if json.loads(await ws.recv()).get("type") != "ready":
            log("[warn] first frame was not 'ready'")
        await ws.send(json.dumps({"type": "subscriptions.set", "requestID": "w1", "chatIDs": ["*"]}))
        log("[connected] subscribed to all chats")
        async for raw in ws:
            try:
                evt = json.loads(raw)
            except Exception:
                continue
            etype = evt.get("type")
            if etype == "chat.upserted":
                for c in evt.get("entries", []):
                    if c.get("id") and c.get("type"):
                        chat_types[c["id"]] = c["type"]
            elif etype == "message.upserted":
                cfg = load_vip()
                for m in evt.get("entries", []):
                    mid = m.get("id") or m.get("messageID")
                    if mid and dedup(mid):
                        continue
                    hit, reason = matches(m, cfg, chat_types.get(m.get("chatID")))
                    if hit:
                        notify(m, reason)


async def main():
    backoff = 2
    while True:
        try:
            await run_once()
            backoff = 2
        except Exception as e:
            log(f"[error] {type(e).__name__}: {e}; reconnecting in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    log("[start] beeper watcher launching")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("[stop] interrupted")
        sys.exit(0)
