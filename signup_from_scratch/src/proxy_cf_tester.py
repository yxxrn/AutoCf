"""Test proxy against Cloudflare challenge page — filter by CF friendliness."""
import sys
sys.path.insert(0, ".")

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import curl_cffi.requests as cr
except ImportError:
    import requests as cr

from src.proxy_manager import load_proxies, Proxy

CF_TEST_URL = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/managed/opt-in/edge.js"


def test_proxy_cf(proxy: Proxy, timeout: int = 12) -> tuple[bool, str]:
    """Return (alive, reason). alive=True means proxy isn't immediately CF-blocked."""
    proxy_url = f"http://{proxy.user}:{proxy.pw}@{proxy.server}" if proxy.has_auth else f"http://{proxy.server}"
    try:
        resp = cr.get(
            "https://dash.cloudflare.com/api/v4/signup",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=timeout,
            impersonate="chrome124",
            allow_redirects=False,
        )
        # If we get a redirect or 4xx that's NOT a CF challenge, it's CF-friendly
        if resp.status_code in (302, 303, 307, 308):
            return True, f"status={resp.status_code} (redirect OK)"
        if resp.status_code == 429:
            return False, "CF_RATE_LIMIT"
        if resp.status_code == 403:
            # Could be CF challenge or just forbidden
            return False, "CF_403"
        if resp.status_code == 503:
            return False, "CF_503"
        return True, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)[:40]


def filter_cf_friendly(proxies: list[Proxy], timeout: int = 12, max_workers: int = 20) -> list[tuple[Proxy, str]]:
    """Return list of (proxy, reason) where proxy is CF-friendly."""
    results: list[tuple[Proxy, str]] = []
    done = 0
    total = len(proxies)
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, total))) as ex:
        futures = {ex.submit(test_proxy_cf, p, timeout): p for p in proxies}
        for fut in as_completed(futures):
            done += 1
            alive, reason = fut.result()
            if alive:
                results.append((futures[fut], reason))
            if done % 50 == 0 or done == total:
                rate = done / (time.time() - t0 + 0.01)
                print(f"  {done}/{total} ({done*100//total}%) - CF-friendly: {len(results)} - {rate:.0f}/s", flush=True)

    print(f"CF-friendly: {len(results)}/{total} in {time.time()-t0:.0f}s")
    return results


if __name__ == "__main__":
    print("Loading proxies...", flush=True)
    proxies = load_proxies("alive_proxies.txt")
    print(f"Loaded {len(proxies)} proxies", flush=True)

    print("\nTesting CF friendliness...", flush=True)
    cf_ok = filter_cf_friendly(proxies, timeout=15, max_workers=15)

    if cf_ok:
        lines = [f"http://{p.host}:{p.port}" for p, _ in cf_ok]
        with open("cf_good_proxies.txt", "w") as f:
            f.write("\n".join(lines))
        print(f"\nSaved {len(lines)} CF-friendly proxies to cf_good_proxies.txt", flush=True)
    else:
        print("\nNo CF-friendly proxies found!")
