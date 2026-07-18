"""Unit tests for rate_limit_guard.py — no browser / no network needed."""

import unittest
from pathlib import Path
import tempfile
import os

from src.rate_limit_guard import RateLimitGuard, RateLimitError


class TestClassifyError(unittest.TestCase):
    def test_turnstile_blocked(self):
        t, is_rl = RateLimitGuard.classify_error("Try again later — challenge")
        self.assertEqual(t, "turnstile_blocked")
        self.assertTrue(is_rl)

    def test_signup_rate_limit(self):
        t, is_rl = RateLimitGuard.classify_error("rate limit exceeded")
        self.assertEqual(t, "signup_rate_limit")
        self.assertTrue(is_rl)

    def test_ip_banned(self):
        t, is_rl = RateLimitGuard.classify_error("IP banned, verify your identity")
        self.assertEqual(t, "ip_banned")
        self.assertTrue(is_rl)

    def test_api_429(self):
        t, is_rl = RateLimitGuard.classify_error("HTTP 429: Too Many Requests")
        self.assertEqual(t, "signup_rate_limit")  # "rate limit" keyword fires first
        self.assertTrue(is_rl)

    def test_email_not_verified_not_rate_limit(self):
        t, is_rl = RateLimitGuard.classify_error("email_not_verified")
        self.assertEqual(t, "email_not_verified")
        self.assertFalse(is_rl)

    def test_unknown_is_rate_limit(self):
        t, is_rl = RateLimitGuard.classify_error("some weird error")
        self.assertEqual(t, "unknown")
        self.assertTrue(is_rl)


class TestRateLimitGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.tmp.close()
        self.score_file = Path(self.tmp.name)

    def tearDown(self):
        try:
            os.unlink(self.score_file)
        except Exception:
            pass

    def test_record_hit_reduces_score(self):
        guard = RateLimitGuard(proxy="http://p:123@1.2.3.4:80", score_file=self.score_file)
        # Default penalty=5, initial score=10. After 2 hits: score=0 → blacklisted.
        guard.record_hit("rate limit exceeded")   # -5 → score=5
        guard.record_hit("IP banned")            # -5 → score=0 → blacklisted
        self.assertTrue(guard.is_blacklisted())

    def test_record_success_rewards(self):
        guard = RateLimitGuard(proxy="http://p:123@1.2.3.4:80", score_file=self.score_file)
        guard.record_hit("rate limit exceeded")
        guard.record_success()
        self.assertFalse(guard.is_blacklisted())

    def test_blacklist_after_penalty(self):
        guard = RateLimitGuard(
            proxy="http://p:123@1.2.3.4:80",
            score_file=self.score_file,
            max_score_penalty=999,
        )
        guard.record_hit("ip banned")
        self.assertTrue(guard.is_blacklisted())

    def test_rate_limit_error_exception(self):
        exc = RateLimitError("turnstile_blocked", "Try again later", cooldown=600)
        self.assertIn("turnstile_blocked", str(exc))
        self.assertEqual(exc.cooldown, 600)


if __name__ == "__main__":
    unittest.main()
