"""Proxy loading, rotation, and authenticated-proxy wiring for nodriver.

nodriver's uc.start() has no proxy param, and Chrome's --proxy-server can't
carry credentials on the CLI. So we:
  1. pass --proxy-server=host:port via browser_args
  2. answer the proxy auth challenge over CDP (Fetch.authRequired)
"""

import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import nodriver as uc
import nodriver.cdp.fetch as fetch

# user:pass@host:port  OR  host:port:user:pass  OR  host:port
_AT = re.compile(r"^(?P<user>[^:@]+):(?P<pw>[^:@]+)@(?P<host>[^:@]+):(?P<port>\d+)$")
_COLON = re.compile(r"^(?P<host>[^:@]+):(?P<port>\d+)(?::(?P<user>[^:@]+):(?P<pw>[^:@]+))?$")


@dataclass
class Proxy:
    host: str
    port: str
    user: Optional[str] = None
    pw: Optional[str] = None

    @property
    def server(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def has_auth(self) -> bool:
        return bool(self.user and self.pw)

    def __str__(self) -> str:
        return f"{self.server}" + (f" (auth: {self.user})" if self.has_auth else "")


def parse_proxy(line: str) -> Optional[Proxy]:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    line = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", line)  # strip any scheme
    m = _AT.match(line) or _COLON.match(line)
    if not m:
        return None
    g = m.groupdict()
    return Proxy(g["host"], g["port"], g.get("user"), g.get("pw"))


def load_proxies(path: str) -> list[Proxy]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        proxy = parse_proxy(line)
        if proxy:
            out.append(proxy)
    return out


def check_proxy(proxy: Proxy, timeout: int = 12) -> bool:
    """Return True if the proxy can reach the internet (CONNECT works)."""
    try:
        import curl_cffi.requests as cr
    except Exception:
        return True  # can't verify — assume usable
    url = f"http://{proxy.user}:{proxy.pw}@{proxy.server}" if proxy.has_auth else f"http://{proxy.server}"
    try:
        resp = cr.get(
            "https://api.ipify.org",
            proxies={"http": url, "https": url},
            timeout=timeout,
            impersonate="chrome124",
        )
        return resp.status_code == 200
    except Exception:
        return False


def filter_alive(proxies: list[Proxy], timeout: int = 8, max_workers: int = 50) -> list[Proxy]:
    """Keep only proxies that pass a live check. Parallel + progress output."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import sys

    alive: list[Proxy] = []
    done = 0
    total = len(proxies)
    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, total))) as ex:
        futures = {ex.submit(check_proxy, p, timeout): p for p in proxies}
        for fut in as_completed(futures):
            done += 1
            if fut.result():
                alive.append(futures[fut])
            sys.stdout.write(f"\r  checked {done}/{total} — alive {len(alive)}")
            sys.stdout.flush()
    sys.stdout.write("\n")
    return alive


class ProxyPool:
    """Rotates through proxies. Shuffled once so runs don't hammer the same IP."""

    def __init__(self, proxies: list[Proxy]):
        self._proxies = list(proxies)
        random.shuffle(self._proxies)
        self._i = 0

    def __bool__(self) -> bool:
        return bool(self._proxies)

    def next(self) -> Optional[Proxy]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._i % len(self._proxies)]
        self._i += 1
        return proxy


async def attach_proxy_auth(browser: uc.Browser, proxy: Proxy) -> None:
    """Enable CDP Fetch auth handling so Chrome answers the proxy 407 challenge."""
    if not proxy.has_auth:
        return
    tab = browser.main_tab
    if tab is None:
        return

    async def _on_auth(event: fetch.AuthRequired):
        # best-effort: Fetch may already be disabled/re-enabled between events
        try:
            await tab.send(
                fetch.continue_with_auth(
                    request_id=event.request_id,
                    auth_challenge_response=fetch.AuthChallengeResponse(
                        response="ProvideCredentials",
                        username=proxy.user,
                        password=proxy.pw,
                    ),
                )
            )
        except Exception:
            pass

    async def _on_paused(event: fetch.RequestPaused):
        try:
            await tab.send(fetch.continue_request(request_id=event.request_id))
        except Exception:
            pass

    tab.add_handler(fetch.AuthRequired, _on_auth)
    tab.add_handler(fetch.RequestPaused, _on_paused)
    await tab.send(fetch.enable(handle_auth_requests=True))


if __name__ == "__main__":
    # ponytail: parser self-check, the one bit with real branching
    assert parse_proxy("u:p@1.2.3.4:80") == Proxy("1.2.3.4", "80", "u", "p")
    assert parse_proxy("1.2.3.4:80:u:p") == Proxy("1.2.3.4", "80", "u", "p")
    assert parse_proxy("1.2.3.4:80") == Proxy("1.2.3.4", "80", None, None)
    assert parse_proxy("http://u:p@1.2.3.4:80").host == "1.2.3.4"
    assert parse_proxy("") is None
    assert parse_proxy("# comment") is None
    pool = ProxyPool([Proxy("a", "1"), Proxy("b", "2")])
    got = {pool.next().host for _ in range(4)}
    assert got == {"a", "b"}
    print("proxy_manager self-check OK")
