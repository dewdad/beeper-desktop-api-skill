import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "beeper-desktop-api"
    / "scripts"
    / "send_poll.py"
)
SPEC = importlib.util.spec_from_file_location("send_poll", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load {SCRIPT}")
send_poll = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = send_poll
SPEC.loader.exec_module(send_poll)


class PollPayloadTests(unittest.TestCase):
    def test_builds_finalized_poll_start_payload(self):
        ids = iter(["answer-a", "answer-b"])
        payload = send_poll.build_poll_payload(
            "Ship it?", ["Yes", "No"], id_factory=lambda: next(ids)
        )

        self.assertEqual(
            payload["m.text"],
            [{"mimetype": "text/plain", "body": "Ship it?\n1. Yes\n2. No"}],
        )
        poll = payload["m.poll"]
        self.assertEqual(poll["question"], {"m.text": [{"body": "Ship it?"}]})
        self.assertEqual(poll["kind"], "m.disclosed")
        self.assertEqual(poll["max_selections"], 1)
        self.assertEqual(
            poll["answers"],
            [
                {"m.id": "answer-a", "m.text": [{"body": "Yes"}]},
                {"m.id": "answer-b", "m.text": [{"body": "No"}]},
            ],
        )

    def test_builds_undisclosed_kind_with_stable_name(self):
        payload = send_poll.build_poll_payload(
            "Ship it?",
            ["Yes", "No"],
            disclosed=False,
            id_factory=iter(["a", "b"]).__next__,
        )
        self.assertEqual(payload["m.poll"]["kind"], "m.undisclosed")

    def test_poll_reference_uses_only_stable_kind_names(self):
        reference = (
            SCRIPT.parents[1] / "references" / "polls.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("m.poll.disclosed", reference)
        self.assertNotIn("m.poll.undisclosed", reference)
        self.assertIn("m.disclosed", reference)
        self.assertIn("m.undisclosed", reference)

    def test_rejects_fewer_than_two_answers(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            send_poll.build_poll_payload("Ship it?", ["Yes"])

    def test_rejects_duplicate_or_blank_answers(self):
        with self.assertRaisesRegex(ValueError, "non-empty and unique"):
            send_poll.build_poll_payload("Ship it?", ["Yes", " yes "])
        with self.assertRaisesRegex(ValueError, "non-empty and unique"):
            send_poll.build_poll_payload("Ship it?", ["Yes", " "])

    def test_rejects_invalid_max_selections(self):
        with self.assertRaisesRegex(ValueError, "max selections"):
            send_poll.build_poll_payload("Ship it?", ["Yes", "No"], max_selections=3)

    def test_rejects_more_than_twenty_answers(self):
        with self.assertRaisesRegex(ValueError, "at most 20"):
            send_poll.build_poll_payload("Choose", [str(i) for i in range(21)])


class URLTests(unittest.TestCase):
    def test_builds_encoded_matrix_send_url(self):
        url = send_poll.build_send_url(
            "https://matrix.example/", "!room:id", "txn / one"
        )
        self.assertEqual(
            url,
            "https://matrix.example/_matrix/client/v3/rooms/"
            "%21room%3Aid/send/m.poll.start/txn%20%2F%20one",
        )

    def test_rejects_non_https_matrix_homeserver(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            send_poll.build_send_url("http://matrix.example", "!room:id", "txn")


class LocalSessionTests(unittest.TestCase):
    def test_reads_matrix_session_only_from_requested_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "index.db"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE key_values (key TEXT PRIMARY KEY, value JSON NOT NULL)")
            con.execute(
                "INSERT INTO key_values(key, value) VALUES (?, ?)",
                (
                    "beeperState",
                    json.dumps(
                        {
                            "access_token": "matrix-token",
                            "homeserver": "https://matrix.example/",
                        }
                    ),
                ),
            )
            con.commit()
            con.close()

            session = send_poll.load_local_matrix_session(Path(tmp))

        self.assertEqual(session.token, "matrix-token")
        self.assertEqual(session.homeserver, "https://matrix.example")


class CapabilityTests(unittest.TestCase):
    def test_accepts_writable_chat_with_native_poll_support(self):
        chat = {
            "id": "!room:id",
            "accountID": "whatsapp",
            "isReadOnly": False,
            "capabilities": {"poll": 2},
        }
        send_poll.validate_chat_capability(chat, "!room:id")

    def test_rejects_wrong_room_read_only_or_unsupported_chat(self):
        cases = [
            ({"id": "!other:id", "capabilities": {"poll": 2}}, "different chat"),
            ({"id": "!room:id", "isReadOnly": True, "capabilities": {"poll": 2}}, "read-only"),
            ({"id": "!room:id", "isReadOnly": False, "capabilities": {"poll": 1}}, "not supported"),
        ]
        for chat, message in cases:
            with self.subTest(chat=chat):
                with self.assertRaisesRegex(ValueError, message):
                    send_poll.validate_chat_capability(chat, "!room:id")


class SendAndVerifyTests(unittest.TestCase):
    def test_sends_with_put_and_reads_back_exact_event(self):
        payload = send_poll.build_poll_payload(
            "Ship it?", ["Yes", "No"], id_factory=iter(["a", "b"]).__next__
        )
        calls = []

        def requester(url, token, **kwargs):
            calls.append((url, token, kwargs))
            if kwargs.get("method") == "PUT":
                return {"event_id": "$event:id"}
            return {
                "event_id": "$event:id",
                "room_id": "!room:id",
                "type": "m.poll.start",
                "content": payload,
            }

        result = send_poll.send_and_verify_poll(
            send_poll.MatrixSession("https://matrix.example", "secret"),
            "!room:id",
            payload,
            transaction_id="txn-1",
            requester=requester,
        )

        self.assertEqual(result["event_id"], "$event:id")
        self.assertTrue(result["verified"])
        self.assertEqual(calls[0][2]["method"], "PUT")
        self.assertEqual(calls[0][2]["payload"], payload)
        self.assertEqual(calls[1][2].get("method", "GET"), "GET")
        self.assertNotIn("secret", json.dumps(result))

    def test_rejects_mismatched_read_back(self):
        payload = send_poll.build_poll_payload(
            "Ship it?", ["Yes", "No"], id_factory=iter(["a", "b"]).__next__
        )

        def requester(url, token, **kwargs):
            if kwargs.get("method") == "PUT":
                return {"event_id": "$event:id"}
            return {
                "event_id": "$different:id",
                "room_id": "!room:id",
                "type": "m.poll.start",
                "content": payload,
            }

        with self.assertRaisesRegex(RuntimeError, "read-back did not match"):
            send_poll.send_and_verify_poll(
                send_poll.MatrixSession("https://matrix.example", "secret"),
                "!room:id",
                payload,
                transaction_id="txn-1",
                requester=requester,
            )

    def test_rejects_changed_fallback_on_read_back(self):
        payload = send_poll.build_poll_payload(
            "Ship it?", ["Yes", "No"], id_factory=iter(["a", "b"]).__next__
        )

        def requester(url, token, **kwargs):
            if kwargs.get("method") == "PUT":
                return {"event_id": "$event:id"}
            changed = json.loads(json.dumps(payload))
            changed["m.text"][0]["body"] = "changed"
            return {
                "event_id": "$event:id",
                "room_id": "!room:id",
                "type": "m.poll.start",
                "content": changed,
            }

        with self.assertRaisesRegex(RuntimeError, "read-back did not match"):
            send_poll.send_and_verify_poll(
                send_poll.MatrixSession("https://matrix.example", "secret"),
                "!room:id",
                payload,
                transaction_id="txn-1",
                requester=requester,
            )


class ArgumentSafetyTests(unittest.TestCase):
    def test_help_does_not_offer_command_line_token_flags(self):
        with self.assertRaises(SystemExit) as exit_context:
            with patch.object(sys, "argv", ["send_poll.py", "--help"]):
                with patch("builtins.print"):
                    send_poll.parse_args()
        self.assertEqual(exit_context.exception.code, 0)
        parser_source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"--matrix-token"', parser_source)
        self.assertNotIn('"--desktop-token"', parser_source)
        self.assertNotIn('"--desktop-url"', parser_source)


    def test_local_session_rejects_homeserver_override(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                send_poll,
                "load_desktop_token",
                return_value="desktop-token",
            ), patch.object(
                send_poll,
                "get_chat",
                return_value={
                    "id": "!room:id",
                    "isReadOnly": False,
                    "capabilities": {"poll": 2},
                },
            ), patch.object(
                send_poll,
                "load_local_matrix_session",
                return_value=send_poll.MatrixSession(
                    "https://matrix.example", "matrix-token"
                ),
            ), patch.object(send_poll, "send_and_verify_poll") as sender:
                result = send_poll.main(
                    [
                        "!room:id",
                        "Ship it?",
                        "Yes",
                        "No",
                        "--allow-local-session",
                        "--homeserver",
                        "https://evil.example",
                        "--send",
                    ]
                )
        self.assertEqual(result, 1)
        sender.assert_not_called()


class RedactionTests(unittest.TestCase):
    def test_result_never_contains_tokens(self):
        result = send_poll.public_result(
            event_id="$event:id",
            room_id="!room:id",
            transaction_id="txn-1",
            verified=True,
        )
        encoded = json.dumps(result)
        self.assertNotIn("token", encoded.lower())
        self.assertEqual(result["verified"], True)


if __name__ == "__main__":
    unittest.main()
