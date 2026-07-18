"""
Rate Limit Guard — Adaptive cooldown & backoff untuk Cloudflare signup.

Semua delay dan retry decision centralized di sini, bukan di main.py.
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Optional

# Bobot per jenis error. Negatif = IP di-blacklist, Positif = IP OK.
IP_SCORE_FILE = Path(__file__).parent.parent / "ip_score.json"


def _load_scores() -> dict:
    if IP_SCORE_FILE.exists():
        try:
            return json.loads(IP_SCORE_FILE.read_text())
        except Exception:
            pass
    return {"default": 10, "proxies": {}}


def _save_scores(scores: dict) -> None:
    try:
        IP_SCORE_FILE.write_text(json.dumps(scores, indent=2))
    except Exception:
        pass


def _score_for_proxy(proxy: Optional[str], scores: dict) -> int:
    if not proxy:
        return scores.get("default", 10)
    return scores.get("proxies", {}).get(proxy, 10)


def _penalize(scores: dict, proxy: Optional[str], amount: int = 3) -> dict:
    """Kurangi score IP/proxy. Di bawah 0 = IP di-blacklist."""
    if not proxy:
        scores["default"] = max(0, scores.get("default", 10) - amount)
    else:
        scores.setdefault("proxies", {})
        scores["proxies"][proxy] = max(0, scores["proxies"].get(proxy, 10) - amount)
    return scores


def _reward(scores: dict, proxy: Optional[str]) -> dict:
    """Naikkan score sedikit per success (cap di 10)."""
    if not proxy:
        scores["default"] = min(10, scores.get("default", 10) + 1)
    else:
        scores.setdefault("proxies", {})
        scores["proxies"][proxy] = min(10, scores["proxies"].get(proxy, 10) + 1)
    return scores


class RateLimitGuard:
    """
    Centralized rate limit handler.

    Usage:
        guard = RateLimitGuard(proxy=proxy_str, score_file=path)
        if guard.is_blacklisted():
            raise RuntimeError("IP blacklisted, rotate proxy")

        try:
            await do_signup()
        except RateLimitError as e:
            guard.record_hit(proxy, error=str(e))
            await guard.cooldown()
        else:
            guard.record_success(proxy)
    """

    # Base delay per error type (seconds). Bisa di-override per instance.
    BASE_DELAY = {
        "turnstile_blocked": 600,     # 10 min
        "signup_rate_limit": 900,    # 15 min
        "ip_banned": 3600,           # 1 hour
        "token_rate_limit": 300,      # 5 min
        "api_429": 180,              # 3 min
        "api_403_waf": 600,          # 10 min
        "unknown": 180,              # 3 min fallback
    }

    def __init__(
        self,
        proxy: Optional[str] = None,
        score_file: Optional[Path] = None,
        max_score_penalty: int = 5,
        multiplier: float = 2.0,
        max_cooldown: int = 7200,
    ):
        self.proxy = proxy
        self.score_file = score_file or IP_SCORE_FILE
        self.max_score_penalty = max_score_penalty
        self.multiplier = multiplier
        self.max_cooldown = max_cooldown
        self._hit_count = 0
        self._last_error_type: Optional[str] = None
        self._last_cooldown_until: float = 0

    # ─── Classification ────────────────────────────────────────────────────

    @staticmethod
    def classify_error(error_str: str) -> tuple[str, bool]:
        """
        Klasifikasi error string → (error_type, is_rate_limit).

        Returns:
            error_type: key di BASE_DELAY
            is_rate_limit: True kalau ini masalah rate limit (vs fatal error)
        """
        e = error_str.lower()

        if any(k in e for k in ("turnstile", "try again later", "challenge")):
            return ("turnstile_blocked", True)
        if any(k in e for k in ("rate limit", "too many request", "429")):
            return ("signup_rate_limit", True)
        if any(k in e for k in ("ip", "banned", "block", "captcha", "verify your identity")):
            return ("ip_banned", True)
        if ("token" in e or "api" in e) and ("429" in e or "rate" in e):
            return ("token_rate_limit", True)
        if any(k in e for k in ("api_http_429", "api_waf_403")):
            return ("api_429", True)
        if "403" in e or "forbidden" in e:
            return ("api_403_waf", True)
        if any(k in e for k in ("email not verified", "email_not_verified")):
            return ("email_not_verified", False)  # bukan rate limit, jangan cooldown
        if any(k in e for k in ("redirect failed", "timeout", "connection closed")):
            return ("transient", True)

        return ("unknown", True)

    # ─── Blacklist ────────────────────────────────────────────────────────

    def is_blacklisted(self) -> bool:
        scores = _load_scores()
        return _score_for_proxy(self.proxy, scores) <= 0

    def blacklist(self) -> None:
        scores = _load_scores()
        scores = _penalize(scores, self.proxy, amount=999)
        _save_scores(scores)

    # ─── Recording ────────────────────────────────────────────────────────

    def record_hit(self, error_str: str) -> float:
        """
        Catat error, hitung cooldown yang dibutuhkan.
        Returns: seconds untuk cooldown.
        """
        self._hit_count += 1
        self._last_error_type, is_rl = self.classify_error(error_str)

        if not is_rl:
            return 0

        # Penalize IP score
        scores = _load_scores()
        scores = _penalize(scores, self.proxy, amount=self.max_score_penalty)
        _save_scores(scores)

        base = self.BASE_DELAY.get(self._last_error_type, self.BASE_DELAY["unknown"])
        # Exponential backoff
        delay = min(base * (self.multiplier ** (self._hit_count - 1)), self.max_cooldown)
        self._last_cooldown_until = time.time() + delay
        return delay

    def record_success(self) -> None:
        """Hapus hit count + reward score."""
        self._hit_count = 0
        scores = _load_scores()
        scores = _reward(scores, self.proxy)
        _save_scores(scores)

    def current_cooldown(self) -> float:
        """Sisa cooldown dalam detik. 0 = boleh lanjut."""
        remaining = self._last_cooldown_until - time.time()
        return max(0, remaining)

    # ─── Async wait ───────────────────────────────────────────────────────

    async def cooldown(self, message: str = "") -> None:
        """Async wait sampai cooldown selesai."""
        delay = self.current_cooldown()
        if delay <= 0:
            return

        msg = message or f"[rate-limit] cooldown {delay:.0f}s ({self._last_error_type})"
        print(f"    ⏳ {msg}")

        steps = max(1, int(delay) // 60)
        for i in range(steps, 0, -1):
            print(f"    ⏳ waiting... {i}m remaining")
            await asyncio.sleep(60)
        remaining = delay % 60
        if remaining > 0:
            await asyncio.sleep(remaining)


class RateLimitError(Exception):
    """Signalnya: ini error rate limit, bukan fatal."""

    def __init__(self, error_type: str, original: str, cooldown: float):
        self.error_type = error_type
        self.original = original
        self.cooldown = cooldown
        super().__init__(f"[{error_type}] {original} (cooldown: {cooldown:.0f}s)")


__all__ = ["RateLimitGuard", "RateLimitError"]
