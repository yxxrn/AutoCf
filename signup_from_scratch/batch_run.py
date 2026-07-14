"""Batch signup: 1 proxy = 1 account, discard after use."""
import sys, asyncio, random, json, time
sys.path.insert(0, ".")
from src.proxy_manager import load_proxies
from main import create_account
from src.utils import load_config

def main():
    config = load_config("config.json")
    proxies = load_proxies("alive_proxies.txt")
    random.shuffle(proxies)
    total = 20
    print(f"Proxies: {len(proxies)}, Accounts: {total}, 1 proxy = 1 account")

    results = []
    for i in range(total):
        if not proxies:
            print(f"Out of proxies! {len(results)} done")
            break

        proxy = proxies.pop(0)
        proxy_str = f"http://{proxy.host}:{proxy.port}"
        print(f"\n--- {i+1}/{total} | {proxy.host}:{proxy.port} ---", flush=True)

        try:
            result = asyncio.run(create_account(
                config=config,
                proxy=proxy_str,
                headless=False,
            ))
            ok = result.get("token_valid")
            status = "OK" if ok else "FAIL"
            print(f"  -> {status} | {result.get('email','?')[:40]}", flush=True)
            if not ok:
                err = result.get("error", "")[:80]
                print(f"  Error: {err}", flush=True)
            results.append(result)
        except Exception as e:
            print(f"  EXCEPTION: {e}", flush=True)
            results.append({"status": "error", "email": "N/A", "error": str(e)})

        # Save incrementally
        with open("results.json", "w") as f:
            json.dump(results, f, indent=2)

        if i < total - 1 and proxies:
            print(f"  Sleeping 20s...", flush=True)
            time.sleep(20)

    full = [r for r in results if r.get("token_valid")]
    print(f"\n=== FINAL: {len(full)}/{len(results)} tokens valid ===", flush=True)
    return full, results

if __name__ == "__main__":
    main()
