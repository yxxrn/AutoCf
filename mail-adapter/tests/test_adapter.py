"""Unit tests for mail-adapter pure helpers + route path handling (no Supabase)."""

from __future__ import annotations

import json
import sys
import unittest
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adapter  # noqa: E402


class TestNormalizeMail(unittest.TestCase):
    def test_supabase_field_names(self):
        raw = {
            "from_address": "noreply@cloudflare.com",
            "from_name": "Cloudflare",
            "subject": "Verify your email",
            "text_body": "Click here",
            "html_body": "<p>Click</p>",
            "received_at": "2026-07-11T00:00:00Z",
        }
        out = adapter._normalize_mail(raw, mail_id="abc")
        self.assertEqual(out["id"], "abc")
        self.assertEqual(out["from"], "Cloudflare <noreply@cloudflare.com>")
        self.assertEqual(out["subject"], "Verify your email")
        self.assertEqual(out["text"], "Click here")
        self.assertEqual(out["html"], "<p>Click</p>")
        self.assertEqual(out["body"], "Click here")
        self.assertTrue(out["snippet"].startswith("Click"))

    def test_bluk_style_field_names(self):
        raw = {
            "id": "99",
            "from": "a@b.com",
            "subject": "Hi",
            "text": "plain",
            "html": "<b>x</b>",
            "date": "today",
        }
        out = adapter._normalize_mail(raw)
        self.assertEqual(out["id"], "99")
        self.assertEqual(out["from"], "a@b.com")
        self.assertEqual(out["text"], "plain")
        self.assertEqual(out["html"], "<b>x</b>")


class TestTokenInfoJwt(unittest.TestCase):
    def _fake(self, auth_header: str | None):
        """Minimal stand-in that reuses AdapterHandler JWT helpers without a socket."""
        headers = {}
        if auth_header is not None:
            headers["Authorization"] = auth_header

        class Fake:
            pass

        fake = Fake()
        fake.headers = headers
        # Bind real methods so self._get_jwt() resolves on Fake.
        fake._get_jwt = adapter.AdapterHandler._get_jwt.__get__(fake, Fake)
        fake._get_token_info = adapter.AdapterHandler._get_token_info.__get__(fake, Fake)
        return fake

    def test_embedded_jwt_format(self):
        """owner_token::address is the adapter-issued JWT format."""
        ti = self._fake("Bearer otok::user@example.com")._get_token_info()
        self.assertEqual(ti["owner_token"], "otok")
        self.assertEqual(ti["address"], "user@example.com")

    def test_missing_auth(self):
        self.assertIsNone(self._fake(None)._get_token_info())


class TestAdapterRoutes(unittest.TestCase):
    """HTTP-level tests against a local AdapterHandler with mocked Supabase."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), adapter.AdapterHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _post(self, path: str, body: dict) -> tuple[int, dict]:
        data = json.dumps(body).encode()
        req = Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode())
        except Exception as e:
            # urllib raises HTTPError for 4xx/5xx
            if hasattr(e, "code") and hasattr(e, "read"):
                return e.code, json.loads(e.read().decode())
            raise

    def _get(self, path: str, headers: dict | None = None) -> tuple[int, object]:
        req = Request(self.base + path, headers=headers or {}, method="GET")
        try:
            with urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode())
        except Exception as e:
            if hasattr(e, "code") and hasattr(e, "read"):
                return e.code, json.loads(e.read().decode())
            raise

    def test_unknown_post_path(self):
        status, body = self._post("/nope", {})
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_new_address_paths(self):
        fake = {
            "address": "u@gmilio.web.id",
            "owner_token": "owner123",
            "domain": "gmilio.web.id",
        }
        for path in ("/new_address", "/api/new_address"):
            with patch.object(adapter, "supabase_create", return_value=fake):
                status, body = self._post(path, {"domain": "gmilio.web.id"})
            self.assertEqual(status, 200, msg=path)
            self.assertEqual(body["address"], "u@gmilio.web.id")
            self.assertEqual(body["jwt"], "owner123::u@gmilio.web.id")

    def test_parsed_mails_requires_auth(self):
        status, body = self._get("/parsed_mails")
        self.assertEqual(status, 401)
        self.assertIn("error", body)

    def test_parsed_mails_ok(self):
        with patch.object(
            adapter,
            "supabase_messages",
            return_value=[{"message_id": "m1", "subject": "s"}],
        ), patch.object(
            adapter,
            "supabase_message",
            return_value={
                "from_address": "cf@cloudflare.com",
                "subject": "Verify",
                "text_body": "link",
            },
        ):
            status, body = self._get(
                "/parsed_mails",
                headers={"Authorization": "Bearer otok::u@example.com"},
            )
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["subject"], "Verify")
        self.assertEqual(body[0]["id"], "m1")


if __name__ == "__main__":
    unittest.main()
