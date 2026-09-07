#!/usr/bin/env python3
"""Send an experimental Matrix poll into a Beeper-backed chat.

Dry-run is the default. Pass --send to perform the network write. This helper
uses the Matrix client API because Beeper Desktop's documented /v1 message
writer does not currently expose polls.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


DEFAULT_DESKTOP_URL = "http://127.0.0.1:23373"
DEFAULT_DATA_DIR = Path.home() / ".config" / "BeeperTexts"
DEFAULT_TARGET = Path.home() / ".beeper" / "targets" / "desktop.json"


@dataclass(frozen=True)
class MatrixSession:
    homeserver: str
    token: str


def build_poll_payload(
    question: str,
    answers: Sequence[str],
    *,
    max_selections: int = 1,
    disclosed: bool = True,
    id_factory: Callable[[], object] = uuid.uuid4,
) -> dict:
    question = question.strip()
    normalized = [answer.strip() for answer in answers]
    if not question:
        raise ValueError("question must be non-empty")
    if len(normalized) < 2:
        raise ValueError("a poll requires at least two answers")
    if len(normalized) > 20:
        raise ValueError("a poll allows at most 20 answers")
    if any(not answer for answer in normalized) or len(
        {answer.casefold() for answer in normalized}
    ) != len(normalized):
        raise ValueError("answers must be non-empty and unique")
    if not 1 <= max_selections <= len(normalized):
        raise ValueError("max selections must be between 1 and the answer count")

    answer_objects = [
        {"m.id": str(id_factory()), "m.text": [{"body": answer}]}
        for answer in normalized
    ]
    fallback = "\n".join(
        [question, *(f"{index}. {answer}" for index, answer in enumerate(normalized, 1))]
    )
    return {
        "m.poll": {
            "max_selections": max_selections,
            "question": {"m.text": [{"body": question}]},
            "kind": "m.disclosed" if disclosed else "m.undisclosed",
            "answers": answer_objects,
        },
        "m.text": [{"mimetype": "text/plain", "body": fallback}],
    }


def build_send_url(homeserver: str, room_id: str, transaction_id: str) -> str:
    require_https_homeserver(homeserver)
    base = homeserver.rstrip("/")
    room = urllib.parse.quote(room_id, safe="")
    txn = urllib.parse.quote(transaction_id, safe="")
    return f"{base}/_matrix/client/v3/rooms/{room}/send/m.poll.start/{txn}"


def build_event_url(homeserver: str, room_id: str, event_id: str) -> str:
    require_https_homeserver(homeserver)
    base = homeserver.rstrip("/")
    room = urllib.parse.quote(room_id, safe="")
    event = urllib.parse.quote(event_id, safe="")
    return f"{base}/_matrix/client/v3/rooms/{room}/event/{event}"


def require_https_homeserver(homeserver: str) -> None:
    parsed = urllib.parse.urlsplit(homeserver)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Matrix homeserver must be an HTTPS URL")


def load_local_matrix_session(data_dir: Path) -> MatrixSession:
    db_path = data_dir.expanduser() / "index.db"
    if not db_path.is_file():
        raise ValueError(f"Beeper index database not found: {db_path}")
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT value FROM key_values WHERE key = ?", ("beeperState",)
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise ValueError("beeperState was not found in the Beeper index database")
    state = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    token = state.get("access_token") or state.get("accessToken")
    homeserver = state.get("homeserver") or state.get("homeserver_url")
    if not token or not homeserver:
        raise ValueError("Beeper's local Matrix session is incomplete")
    return MatrixSession(homeserver=homeserver.rstrip("/"), token=token)


def load_desktop_token(target_path: Path = DEFAULT_TARGET) -> str:
    env_token = os.environ.get("BEEPER_ACCESS_TOKEN")
    if env_token:
        return env_token
    try:
        target = json.loads(target_path.expanduser().read_text(encoding="utf-8"))
        token = target["auth"]["accessToken"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "set BEEPER_ACCESS_TOKEN or configure the Beeper CLI desktop target"
        ) from exc
    if not token:
        raise ValueError("the Beeper Desktop API token is empty")
    return token


def request_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: float = 30,
) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error: {exc.reason}") from exc
    return json.loads(body) if body else {}


def validate_chat_capability(chat: dict, room_id: str) -> None:
    if chat.get("id") != room_id:
        raise ValueError("Desktop API returned a different chat")
    if chat.get("isReadOnly"):
        raise ValueError("the target chat is read-only")
    if chat.get("capabilities", {}).get("poll") != 2:
        raise ValueError("native polls are not supported in the target chat")


def get_chat(
    desktop_url: str, desktop_token: str, room_id: str, timeout: float
) -> dict:
    encoded_room = urllib.parse.quote(room_id, safe="")
    return request_json(
        f"{desktop_url.rstrip('/')}/v1/chats/{encoded_room}",
        desktop_token,
        timeout=timeout,
    )


def public_result(
    *, event_id: str, room_id: str, transaction_id: str, verified: bool
) -> dict:
    return {
        "event_id": event_id,
        "room_id": room_id,
        "transaction_id": transaction_id,
        "verified": verified,
    }


def send_and_verify_poll(
    session: MatrixSession,
    room_id: str,
    payload: dict,
    *,
    transaction_id: str,
    timeout: float = 30,
    requester: Callable[..., dict] = request_json,
) -> dict:
    sent = requester(
        build_send_url(session.homeserver, room_id, transaction_id),
        session.token,
        method="PUT",
        payload=payload,
        timeout=timeout,
    )
    event_id = sent.get("event_id")
    if not event_id:
        raise RuntimeError("Matrix send response did not contain event_id")
    event = requester(
        build_event_url(session.homeserver, room_id, event_id),
        session.token,
        timeout=timeout,
    )
    verified = (
        event.get("event_id") == event_id
        and event.get("room_id") == room_id
        and event.get("type") == "m.poll.start"
        and event.get("content", {}) == payload
    )
    if not verified:
        raise RuntimeError("poll event read-back did not match the sent event")
    return public_result(
        event_id=event_id,
        room_id=room_id,
        transaction_id=transaction_id,
        verified=True,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("room_id", help="Exact Beeper/Matrix room ID")
    parser.add_argument("question")
    parser.add_argument("answers", nargs="+", help="At least two answer choices")
    parser.add_argument("--max-selections", type=int, default=1)
    parser.add_argument("--undisclosed", action="store_true")
    parser.add_argument("--homeserver", help="Matrix homeserver URL")
    parser.add_argument(
        "--allow-local-session",
        action="store_true",
        help="Read the Matrix session from Beeper Desktop's local index.db",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument(
        "--send",
        action="store_true",
        help="Perform the write; without this flag only print the payload",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = build_poll_payload(
            args.question,
            args.answers,
            max_selections=args.max_selections,
            disclosed=not args.undisclosed,
        )
        if not args.send:
            print(json.dumps({"dry_run": True, "room_id": args.room_id, "content": payload}, ensure_ascii=False, indent=2))
            return 0

        desktop_token = load_desktop_token()
        chat = get_chat(DEFAULT_DESKTOP_URL, desktop_token, args.room_id, args.timeout)
        validate_chat_capability(chat, args.room_id)

        matrix_token = os.environ.get("BEEPER_MATRIX_ACCESS_TOKEN")
        if matrix_token:
            if not args.homeserver:
                raise ValueError(
                    "--homeserver is required when BEEPER_MATRIX_ACCESS_TOKEN is set"
                )
            session = MatrixSession(args.homeserver.rstrip("/"), matrix_token)
        elif args.allow_local_session:
            if args.homeserver:
                raise ValueError(
                    "--homeserver cannot override the homeserver of a local session"
                )
            session = load_local_matrix_session(args.data_dir)
        else:
            raise ValueError(
                "set BEEPER_MATRIX_ACCESS_TOKEN and --homeserver, or explicitly pass "
                "--allow-local-session"
            )

        transaction_id = f"beeper-poll-{time.time_ns()}"
        result = send_and_verify_poll(
            session,
            args.room_id,
            payload,
            transaction_id=transaction_id,
            timeout=args.timeout,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
