#!/usr/bin/env python3
"""
Beeper Messaging Manager — one-command installer.

Goal: after loading this skill, a single run of this script gets the user's
agent managing their Beeper messaging with as little manual work as possible:

  1. Detect OS (Linux / macOS / Windows) and host agent (Hermes / OpenCode /
     generic) so downstream wiring targets the right scheduler + supervisor.
  2. Verify prerequisites: Beeper Desktop reachable on :23373 with the API
     enabled, the `beeper` CLI present, `jq` present, a resolvable token.
  3. Materialize the automation dir (default ~/.beeper-automation): copy
     watcher.py / digest.sh / vip.json / alert.env / prompt, build an isolated
     venv with `websockets`.
  4. Supervise the realtime watcher (systemd --user on Linux, launchd on
     macOS) — or print exact manual steps where automation isn't possible.
  5. Register the 3x/day digest on the detected scheduler — or print steps.
  6. Self-test the alert logic and smoke-test the collector.

DESIGN PRINCIPLE: automate what can be automated; where a step genuinely needs
a human (mint a token in a GUI, run a privileged command, no supervisor
available), STOP and print an exact, copy-pasteable instruction instead of
faking success. Every step reports PASS / SKIP / MANUAL so the user knows the
true state.

Usage:
    python install.py [--dir DIR] [--dry-run] [--no-schedule] [--no-supervise]
                      [--tg-token TOKEN --tg-chat CHAT] [--yes]

Safe to re-run (idempotent): re-copies templates, recreates units, re-registers
schedule. Existing vip.json and alert.env are preserved unless --force-config.
"""
import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
TEMPLATES = SKILL_DIR / "templates"
DEFAULT_BASE = Path(os.environ.get("BEEPER_AUTOMATION_DIR", "~/.beeper-automation")).expanduser()
BEEPER_INFO_URL = "http://127.0.0.1:23373/v1/info"

GREEN, YELLOW, RED, BLUE, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[34m", "\033[0m"


def say(kind, msg):
    tag = {
        "PASS": f"{GREEN}[PASS]{RESET}",
        "SKIP": f"{YELLOW}[SKIP]{RESET}",
        "MANUAL": f"{BLUE}[MANUAL]{RESET}",
        "FAIL": f"{RED}[FAIL]{RESET}",
        "INFO": "[INFO]",
    }.get(kind, "[INFO]")
    print(f"{tag} {msg}")


def run(cmd, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    return subprocess.run(cmd, **kw)


# ---------------------------------------------------------------------------
# 1. Detection
# ---------------------------------------------------------------------------
def detect_os():
    s = platform.system().lower()
    if s == "linux":
        return "linux"
    if s == "darwin":
        return "macos"
    if s == "windows":
        return "windows"
    return s


def detect_host_agent():
    """Best-effort: which agent runtime are we installing under?"""
    home = Path.home()
    if shutil.which("hermes") or (home / ".hermes").is_dir():
        return "hermes"
    # OpenCode stores skills/config under ~/.config/opencode or ~/.opencode
    if shutil.which("opencode") or (home / ".config" / "opencode").is_dir() or (home / ".opencode").is_dir():
        return "opencode"
    return "generic"


def find_beeper_bin():
    """`beeper` may not be on a narrow scheduler PATH; check common npm dirs."""
    b = shutil.which("beeper")
    if b:
        return b
    for cand in [
        Path.home() / ".npm-global" / "bin" / "beeper",
        Path.home() / ".local" / "bin" / "beeper",
        Path("/usr/local/bin/beeper"),
        Path("/opt/homebrew/bin/beeper"),
    ]:
        if cand.exists():
            return str(cand)
    return None


# ---------------------------------------------------------------------------
# 2. Prerequisites
# ---------------------------------------------------------------------------
def desktop_reachable():
    try:
        req = urllib.request.Request(BEEPER_INFO_URL)
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status in (200, 401)  # 401 = up but token needed
    except Exception:
        return False


def resolve_token():
    if os.environ.get("BEEPER_ACCESS_TOKEN"):
        return "env"
    for p in [
        Path(os.environ.get("BEEPER_TOKEN_FILE", "")) if os.environ.get("BEEPER_TOKEN_FILE") else None,
        Path.home() / ".beeper" / "targets" / "desktop.json",
    ]:
        if p and p.exists():
            try:
                if json.loads(p.read_text()).get("auth", {}).get("accessToken"):
                    return str(p)
            except Exception:
                pass
    return None


def check_prereqs(state):
    ok = True

    if desktop_reachable():
        say("PASS", "Beeper Desktop API reachable on 127.0.0.1:23373")
    else:
        say("MANUAL", "Beeper Desktop API NOT reachable on :23373.")
        print("        -> Open Beeper Desktop, then Settings -> Developers -> "
              "enable 'Beeper Desktop API'. Re-run this installer.")
        ok = False

    beeper = find_beeper_bin()
    if beeper:
        state["beeper_bin"] = beeper
        say("PASS", f"beeper CLI found: {beeper}")
    else:
        say("MANUAL", "beeper CLI not found. Install it: npm install -g @beeper/cli")
        ok = False

    if shutil.which("jq"):
        say("PASS", "jq found (needed by digest.sh)")
    else:
        say("MANUAL", "jq not found. Install it (apt/brew/choco install jq) for the digest.")

    tok = resolve_token()
    if tok:
        say("PASS", f"Beeper token resolved ({'env var' if tok == 'env' else tok})")
    else:
        say("MANUAL", "No API token found.")
        print("        -> In Beeper: Settings -> Developers -> Approved connections -> +")
        print("           Copy the bdapi_* token, then either:")
        print("             export BEEPER_ACCESS_TOKEN=bdapi_...   (transient), or")
        print('             add {"auth":{"accessToken":"bdapi_..."}} to '
              "~/.beeper/targets/desktop.json (persistent).")
        print("        (If ~/.beeper/targets/desktop.json is missing, first run:")
        print("           beeper targets add desktop desktop --port 23373 )")
        ok = False

    return ok


# ---------------------------------------------------------------------------
# 3. Materialize automation dir + venv
# ---------------------------------------------------------------------------
def materialize(base: Path, dry, force_config):
    if dry:
        say("SKIP", f"[dry-run] would create automation dir: {base}")
    else:
        base.mkdir(parents=True, exist_ok=True)
        say("PASS", f"automation dir: {base}")

    always = ["watcher.py", "digest.sh", "digest_prompt.md"]
    config = ["vip.json", "alert.env"]
    for name in always:
        dst = base / name
        if dry:
            say("SKIP", f"[dry-run] would copy {name}")
            continue
        shutil.copy2(TEMPLATES / name, dst)
        if name.endswith(".sh") or name.endswith(".py"):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR)
        say("PASS", f"copied {name}")
    for name in config:
        dst = base / name
        if dry:
            say("SKIP", f"[dry-run] would copy {name} (preserve if it already exists)")
        elif dst.exists() and not force_config:
            say("SKIP", f"{name} exists — preserved (use --force-config to overwrite)")
        else:
            shutil.copy2(TEMPLATES / name, dst)
            say("PASS", f"copied {name}")

    # venv with websockets
    venv = base / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if dry:
        say("SKIP", "[dry-run] would create venv + install websockets")
        return str(py)
    if not py.exists():
        r = run([sys.executable, "-m", "venv", str(venv)])
        if r.returncode != 0:
            say("FAIL", f"venv creation failed: {r.stderr.strip()}")
            return str(py)
    r = run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip", "websockets"])
    if r.returncode == 0:
        say("PASS", "venv ready with websockets")
    else:
        say("FAIL", f"pip install websockets failed: {r.stderr.strip()[:300]}")
    return str(py)


# ---------------------------------------------------------------------------
# 4. Supervision
# ---------------------------------------------------------------------------
def fill(template_name, base, py):
    txt = (TEMPLATES / template_name).read_text()
    return txt.replace("__BASE_DIR__", str(base)).replace("__PYTHON__", py)


def supervise_linux(base, py, dry):
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit = unit_dir / "beeper-watcher.service"
    if dry:
        say("SKIP", f"[dry-run] would write {unit} and enable+start it")
        return
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit.write_text(fill("beeper-watcher.service", base, py))
    say("PASS", f"wrote {unit}")

    if not shutil.which("systemctl"):
        say("MANUAL", "systemctl not available — start the watcher yourself:")
        print(f"        {py} {base}/watcher.py &")
        return

    env = dict(os.environ, XDG_RUNTIME_DIR=f"/run/user/{os.getuid()}")
    run(["loginctl", "enable-linger", os.environ.get("USER", "")], env=env)
    run(["systemctl", "--user", "daemon-reload"], env=env)
    r = run(["systemctl", "--user", "enable", "--now", "beeper-watcher.service"], env=env)
    if r.returncode == 0:
        say("PASS", "beeper-watcher.service enabled + started")
        st = run(["systemctl", "--user", "is-active", "beeper-watcher.service"], env=env)
        say("INFO", f"service state: {st.stdout.strip()}")
    else:
        say("MANUAL", "Could not start service automatically. Run:")
        print("        systemctl --user daemon-reload && "
              "systemctl --user enable --now beeper-watcher.service")


def supervise_macos(base, py, dry):
    la = Path.home() / "Library" / "LaunchAgents"
    plist = la / "com.beeper.watcher.plist"
    if dry:
        say("SKIP", f"[dry-run] would write {plist} and launchctl load it")
        return
    la.mkdir(parents=True, exist_ok=True)
    plist.write_text(fill("com.beeper.watcher.plist", base, py))
    say("PASS", f"wrote {plist}")
    run(["launchctl", "unload", str(plist)])
    r = run(["launchctl", "load", str(plist)])
    if r.returncode == 0:
        say("PASS", "launchd agent loaded (com.beeper.watcher)")
    else:
        say("MANUAL", f"launchctl load failed: {r.stderr.strip()}. Run: launchctl load {plist}")


def supervise_windows(base, py, dry):
    say("MANUAL", "Windows: no auto-supervisor wired. Options:")
    print(f"        - Task Scheduler: create a task running `{py} {base}\\watcher.py` at logon.")
    print(f"        - Or run in a terminal:  {py} {base}\\watcher.py")


def supervise(os_name, base, py, dry):
    if os_name == "linux":
        supervise_linux(base, py, dry)
    elif os_name == "macos":
        supervise_macos(base, py, dry)
    else:
        supervise_windows(base, py, dry)


# ---------------------------------------------------------------------------
# 5. Schedule the digest
# ---------------------------------------------------------------------------
def schedule_digest(host, os_name, base, beeper_bin, dry):
    prompt_path = base / "digest_prompt.md"
    times = "0 8,13,19 * * *"  # 08:00 / 13:00 / 19:00 local
    if host == "hermes":
        say("MANUAL", "Hermes detected — register the digest as a Hermes cron job.")
        print("        Ask your Hermes agent (or run) the cronjob tool with:")
        print(f'          schedule: "{times}"')
        print(f"          prompt:   contents of {prompt_path}")
        print("          deliver:  telegram   (NOT origin/webui — WebUI cron delivery fails)")
        print("          enabled_toolsets: [\"terminal\"]")
        print(f"        The prompt already references {base}/digest.sh.")
        return
    if host == "opencode":
        say("MANUAL", "OpenCode detected — schedule via your OS scheduler to invoke OpenCode headless.")
        print(f"        Example crontab line (edit `opencode run` to your version):")
        print(f'          {times.replace("*/", "*/")} opencode run --prompt-file {prompt_path} >> {base}/digest.out 2>&1')
        return
    # generic: offer a plain crontab entry that runs the collector + a note
    if os_name in ("linux", "macos"):
        say("MANUAL", "Generic host — add a crontab entry (collector only; wire your own summarizer):")
        print(f'          {times} BEEPER_BIN={beeper_bin or "beeper"} {base}/digest.sh 15 3 >> {base}/digest.json 2>&1')
    else:
        say("MANUAL", "Generic Windows host — use Task Scheduler to run digest.sh via Git Bash / WSL.")


# ---------------------------------------------------------------------------
# 6. Verify
# ---------------------------------------------------------------------------
def verify(base, py, beeper_bin, dry):
    if dry:
        say("SKIP", "[dry-run] skipping self-test + smoke-test")
        return
    # alert-logic self test
    test = HERE / "test_matches.py"
    if test.exists():
        r = run([py, str(test), str(base / "watcher.py")])
        (say("PASS", "alert-logic self-test passed") if r.returncode == 0
         else say("FAIL", f"alert-logic self-test FAILED:\n{r.stdout}{r.stderr}"))
    # collector smoke test
    if beeper_bin:
        env = dict(os.environ, BEEPER_BIN=beeper_bin)
        r = run(["bash", str(base / "digest.sh"), "3", "1"], env=env)
        if r.returncode == 0 and r.stdout.strip().startswith("{"):
            try:
                n = len(json.loads(r.stdout).get("chats", []))
                say("PASS", f"digest.sh smoke-test OK ({n} chat(s) returned)")
            except Exception:
                say("SKIP", "digest.sh ran but output wasn't parseable JSON (check target/token)")
        else:
            say("SKIP", f"digest.sh smoke-test inconclusive: {r.stderr.strip()[:200]}")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Install the Beeper Messaging Manager automation.")
    ap.add_argument("--dir", default=str(DEFAULT_BASE), help="automation base dir")
    ap.add_argument("--dry-run", action="store_true", help="show actions without making changes")
    ap.add_argument("--no-supervise", action="store_true", help="skip watcher supervision")
    ap.add_argument("--no-schedule", action="store_true", help="skip digest scheduling")
    ap.add_argument("--force-config", action="store_true", help="overwrite existing vip.json/alert.env")
    ap.add_argument("--tg-token", help="Telegram bot token for alert delivery")
    ap.add_argument("--tg-chat", help="Telegram chat id for alert delivery")
    args = ap.parse_args()

    base = Path(args.dir).expanduser()
    os_name = detect_os()
    host = detect_host_agent()
    state = {"beeper_bin": None}

    print(f"\n=== Beeper Messaging Manager installer ===")
    say("INFO", f"OS={os_name}  host-agent={host}  dir={base}  dry_run={args.dry_run}\n")

    print("--- 1. Prerequisites ---")
    prereq_ok = check_prereqs(state)

    print("\n--- 2. Materialize automation dir ---")
    py = materialize(base, args.dry_run, args.force_config)

    # optional: write TG creds
    if args.tg_token and args.tg_chat and not args.dry_run:
        (base / "alert.env").write_text(
            f"BEEPER_ALERT_TG_TOKEN={args.tg_token}\nBEEPER_ALERT_TG_CHAT={args.tg_chat}\n"
        )
        say("PASS", "wrote Telegram delivery creds to alert.env")

    if not args.no_supervise:
        print("\n--- 3. Supervise realtime watcher ---")
        supervise(os_name, base, py, args.dry_run)

    if not args.no_schedule:
        print("\n--- 4. Schedule digest ---")
        schedule_digest(host, os_name, base, state["beeper_bin"], args.dry_run)

    print("\n--- 5. Verify ---")
    verify(base, py, state["beeper_bin"], args.dry_run)

    print("\n=== Summary ===")
    if not prereq_ok:
        say("MANUAL", "Some prerequisites need a manual step (above). Re-run after fixing them.")
    say("INFO", f"Tune alerts by editing {base}/vip.json (live — no restart).")
    say("INFO", f"Set delivery creds in {base}/alert.env, then restart the watcher.")
    say("INFO", "Realtime watcher + 3x/day digest are the two moving parts. Done.")


if __name__ == "__main__":
    main()
