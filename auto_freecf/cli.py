from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import DEFAULT_MODEL, collect, export_csv, export_json, load_tokens


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Auto-FreeCF: Cloudflare Workers AI credential collector")
    ap.add_argument("--mode", choices=["manual-token", "session-import", "solver-assisted"], default="manual-token",
                    help="Automation mode. Only manual-token is fully implemented; others print requirements.")
    ap.add_argument("--token", help="Cloudflare API token")
    ap.add_argument("--token-file", help="File containing one Cloudflare API token per line")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Workers AI model to test")
    ap.add_argument("--out-json", default="exports/workers_ai_accounts.json")
    ap.add_argument("--out-csv", default="exports/workers_ai_accounts.csv")
    ap.add_argument("--no-test", action="store_true", help="Do not call Workers AI test endpoint")
    ap.add_argument("--print-full-auto-requirements", action="store_true", help="Print requirements for full automation modes")
    args = ap.parse_args(argv)

    if args.mode != "manual-token" or args.print_full_auto_requirements:
        print("Full automation modes:")
        print("1) session-import: requires a logged-in Cloudflare dashboard session cookie exported from user-owned browser/phone.")
        print("2) solver-assisted: requires residential/mobile proxy, managed-challenge clearance provider, Turnstile solver, temp-mail inbox, and careful retry/rate limits.")
        print("Cloudflare does not provide a public API for creating new dashboard users from zero.")
        if args.mode != "manual-token":
            return 0

    tokens = load_tokens(args.token, args.token_file)
    if not tokens:
        print("No token. Use --token, --token-file, or CF_API_TOKEN env.", file=sys.stderr)
        return 2

    all_rows = []
    for idx, token in enumerate(tokens, 1):
        print(f"\n=== TOKEN {idx}/{len(tokens)} ===")
        try:
            rows, logs = collect(token, args.model, test=not args.no_test)
            all_rows.extend(rows)
            for line in logs:
                print(line)
        except Exception as e:
            print(f"ERROR: {e}")

    export_json(Path(args.out_json), all_rows)
    export_csv(Path(args.out_csv), all_rows)
    print(f"\nexport_json: {args.out_json}")
    print(f"export_csv:  {args.out_csv}")
    print(f"rows: {len(all_rows)}")
    return 0 if all_rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
