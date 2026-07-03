from __future__ import annotations

import csv
import json
import os
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
                "User-Agent": "auto-freecf/1.0",
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
        return self._check(self.client.get(f"{CF_API}/user/tokens/verify"))["result"]

    def user(self) -> dict[str, Any]:
        return self._check(self.client.get(f"{CF_API}/user"))["result"]

    def accounts(self) -> list[dict[str, Any]]:
        return self._check(self.client.get(f"{CF_API}/accounts", params={"per_page": 50}))["result"]

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


def load_tokens(token: str | None = None, token_file: str | None = None) -> list[str]:
    toks: list[str] = []
    if token:
        toks.append(token.strip())
    if token_file:
        p = Path(token_file)
        if not p.exists():
            raise FileNotFoundError(f"token file not found: {p}")
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                toks.append(line)
    env_tok = os.environ.get("CF_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    if env_tok:
        toks.append(env_tok.strip())

    seen: set[str] = set()
    out: list[str] = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def export_json(path: Path, rows: list[AccountExport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(r) for r in rows], indent=2))


def export_csv(path: Path, rows: list[AccountExport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["email", "account_id", "account_name", "api_token", "workers_ai_ok", "workers_ai_error"]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(asdict(row))


def collect(token: str, model: str = DEFAULT_MODEL, test: bool = True) -> tuple[list[AccountExport], list[str]]:
    logs: list[str] = []
    rows: list[AccountExport] = []
    cf = Cloudflare(token)
    vt = cf.verify_token()
    logs.append(f"token_status: {vt.get('status')} | id: {vt.get('id')}")
    try:
        user = cf.user()
        email = user.get("email")
        logs.append(f"user_email: {email}")
    except Exception as e:
        email = None
        logs.append(f"user_email: unavailable ({e})")

    accounts = cf.accounts()
    logs.append(f"accounts: {len(accounts)}")
    for acc in accounts:
        aid = acc.get("id")
        name = acc.get("name") or ""
        if test:
            ok, err = cf.test_workers_ai(aid, model)
        else:
            ok, err = True, None
        status = "OK" if ok else f"FAIL: {err}"
        logs.append(f"- {name} | {aid} | workers_ai: {status}")
        rows.append(AccountExport(email, aid, name, token, ok, err))
    return rows, logs
