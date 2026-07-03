#!/usr/bin/env python3
"""
Cloudflare Workers AI credential manager.
No browser. Uses official Cloudflare API.

Purpose:
- Verify a Cloudflare API token
- List Account IDs
- Test Workers AI access on an account
- Export clean JSON/CSV credentials for downstream routers/manual injection

Important:
Cloudflare does not expose a public API to create new user accounts. Token creation via API
requires an existing token with API Tokens Edit/Create Additional Tokens permission.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

CF_API = "https://api.cloudflare.com/client/v4"
DEFAULT_MODEL = "@cf/meta/llama-3.1-8b-instruct"


@dataclass
class AccountExport:
    email: str | None
    account_id: str
    account_name: str
    api_token: str
    workers_ai_ok: bool
    workers_ai_error: str | None = None


class CFError(RuntimeError):
    pass


class Cloudflare:
    def __init__(self, token: str, timeout: int = 45):
        self.token = token.strip()
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "cf-workerai-manager/1.0",
            },
        )

    def _check(self, r: httpx.Response) -> dict[str, Any]:
        try:
            data = r.json()
        except Exception as e:
            raise CFError(f"Non-JSON response {r.status_code}: {r.text[:300]}") from e
        if not data.get("success"):
            errs = data.get("errors") or []
            msg = "; ".join(f"{e.get('code')}: {e.get('message')}" for e in errs) or str(data)
            raise CFError(msg)
        return data

    def verify_token(self) -> dict[str, Any]:
        r = self.client.get(f"{CF_API}/user/tokens/verify")
        return self._check(r)["result"]

    def user(self) -> dict[str, Any]:
        r = self.client.get(f"{CF_API}/user")
        return self._check(r)["result"]

    def accounts(self) -> list[dict[str, Any]]:
        r = self.client.get(f"{CF_API}/accounts", params={"per_page": 50})
        return self._check(r)["result"]

    def test_workers_ai(self, account_id: str, model: str = DEFAULT_MODEL) -> tuple[bool, str | None]:
        payload = {
            "messages": [
                {"role": "system", "content": "Return only OK."},
                {"role": "user", "content": "ping"},
            ],
            "max_tokens": 8,
        }
        try:
            r = self.client.post(f"{CF_API}/accounts/{account_id}/ai/run/{model}", json=payload)
            data = r.json()
        except Exception as e:
            return False, f"request_error: {e}"
        if data.get("success"):
            return True, None
        errs = data.get("errors") or []
        msg = "; ".join(f"{e.get('code')}: {e.get('message')}" for e in errs) or r.text[:400]
        return False, msg


def load_tokens(args: argparse.Namespace) -> list[str]:
    toks: list[str] = []
    if args.token:
        toks.append(args.token.strip())
    if args.token_file:
        p = Path(args.token_file)
        if not p.exists():
            raise SystemExit(f"token file not found: {p}")
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                toks.append(line)
    env_tok = os.environ.get("CF_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    if env_tok:
        toks.append(env_tok.strip())
    # Preserve order, dedupe
    seen = set()
    out = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    if not out:
        raise SystemExit("No token. Use --token, --token-file, or CF_API_TOKEN env.")
    return out


def export_json(path: Path, rows: list[AccountExport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(r) for r in rows], indent=2))


def export_csv(path: Path, rows: list[AccountExport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [
            "email", "account_id", "account_name", "api_token", "workers_ai_ok", "workers_ai_error"
        ])
        w.writeheader()
        for row in rows:
            w.writerow(asdict(row))


def main() -> int:
    ap = argparse.ArgumentParser(description="Cloudflare Workers AI credential manager")
    ap.add_argument("--token", help="Cloudflare API token")
    ap.add_argument("--token-file", help="File containing one Cloudflare API token per line")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Workers AI model to test")
    ap.add_argument("--out-json", default="/root/cf-account-bot/exports/workers_ai_accounts.json")
    ap.add_argument("--out-csv", default="/root/cf-account-bot/exports/workers_ai_accounts.csv")
    ap.add_argument("--no-test", action="store_true", help="Do not call Workers AI test endpoint")
    args = ap.parse_args()

    rows: list[AccountExport] = []
    tokens = load_tokens(args)

    for idx, token in enumerate(tokens, 1):
        print(f"\n=== TOKEN {idx}/{len(tokens)} ===")
        cf = Cloudflare(token)
        try:
            vt = cf.verify_token()
            print(f"token_status: {vt.get('status')} | id: {vt.get('id')}")
            try:
                user = cf.user()
                email = user.get("email")
                print(f"user_email: {email}")
            except Exception as e:
                email = None
                print(f"user_email: unavailable ({e})")

            accounts = cf.accounts()
            if not accounts:
                print("accounts: none")
                continue
            print(f"accounts: {len(accounts)}")

            for acc in accounts:
                aid = acc.get("id")
                name = acc.get("name") or ""
                ok, err = (False, None)
                if not args.no_test:
                    ok, err = cf.test_workers_ai(aid, args.model)
                else:
                    ok = True
                status = "OK" if ok else f"FAIL: {err}"
                print(f"- {name} | {aid} | workers_ai: {status}")
                rows.append(AccountExport(
                    email=email,
                    account_id=aid,
                    account_name=name,
                    api_token=token,
                    workers_ai_ok=ok,
                    workers_ai_error=err,
                ))
        except Exception as e:
            print(f"ERROR: {e}")

    export_json(Path(args.out_json), rows)
    export_csv(Path(args.out_csv), rows)
    print(f"\nexport_json: {args.out_json}")
    print(f"export_csv:  {args.out_csv}")
    print(f"rows: {len(rows)}")
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
