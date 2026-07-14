"""Unit tests for proxy_manager.parse_proxy / ProxyPool (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.proxy_manager import Proxy, ProxyPool, parse_proxy  # noqa: E402


class TestParseProxy(unittest.TestCase):
    def test_user_pass_at_host(self):
        p = parse_proxy("u:p@1.2.3.4:8080")
        self.assertEqual(p, Proxy("1.2.3.4", "8080", "u", "p"))
        self.assertTrue(p.has_auth)
        self.assertEqual(p.server, "1.2.3.4:8080")

    def test_host_port_user_pass(self):
        p = parse_proxy("1.2.3.4:80:u:p")
        self.assertEqual(p, Proxy("1.2.3.4", "80", "u", "p"))

    def test_host_port_only(self):
        p = parse_proxy("1.2.3.4:3128")
        self.assertEqual(p, Proxy("1.2.3.4", "3128", None, None))
        self.assertFalse(p.has_auth)

    def test_scheme_stripped_http(self):
        p = parse_proxy("http://u:p@10.0.0.1:8888")
        self.assertIsNotNone(p)
        self.assertEqual(p.host, "10.0.0.1")
        self.assertEqual(p.port, "8888")
        self.assertEqual(p.user, "u")
        self.assertEqual(p.pw, "p")

    def test_scheme_stripped_socks5(self):
        p = parse_proxy("socks5://user:pass@9.9.9.9:1080")
        self.assertIsNotNone(p)
        self.assertEqual(p.host, "9.9.9.9")
        self.assertEqual(p.port, "1080")
        self.assertEqual(p.user, "user")
        self.assertEqual(p.pw, "pass")

    def test_scheme_stripped_socks4(self):
        p = parse_proxy("socks4://1.1.1.1:1080")
        self.assertIsNotNone(p)
        self.assertEqual(p.host, "1.1.1.1")
        self.assertEqual(p.port, "1080")
        self.assertIsNone(p.user)

    def test_empty_and_comment(self):
        self.assertIsNone(parse_proxy(""))
        self.assertIsNone(parse_proxy("   "))
        self.assertIsNone(parse_proxy("# comment"))

    def test_invalid_lines(self):
        self.assertIsNone(parse_proxy("not-a-proxy"))
        self.assertIsNone(parse_proxy("host-only"))


class TestProxyPool(unittest.TestCase):
    def test_empty_pool(self):
        pool = ProxyPool([])
        self.assertFalse(pool)
        self.assertIsNone(pool.next())

    def test_rotation_covers_all(self):
        proxies = [Proxy("a", "1"), Proxy("b", "2"), Proxy("c", "3")]
        pool = ProxyPool(proxies)
        self.assertTrue(pool)
        got = {pool.next().host for _ in range(6)}
        self.assertEqual(got, {"a", "b", "c"})


if __name__ == "__main__":
    unittest.main()
