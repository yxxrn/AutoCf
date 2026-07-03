<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="Auto-FreeCF logo">
</p>

<h1 align="center">Auto-FreeCF</h1>
<p align="center">Cloudflare Workers AI Account ID and token collector with explicit automation modes.</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-v1.0.0-181717?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-2ea44f?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Mode" src="https://img.shields.io/badge/browser-none-ff6b35?style=flat-square">
  <img alt="Cloudflare" src="https://img.shields.io/badge/Cloudflare-Workers%20AI-F38020?style=flat-square&logo=cloudflare&logoColor=white">
</p>

<p align="center">
  <a href="#features"><img alt="Features" src="https://img.shields.io/badge/%E2%9C%A8-features-181717?style=flat-square"></a>
  <a href="#quick-start"><img alt="Quick Start" src="https://img.shields.io/badge/%E2%9A%A1-quick%20start-2ea44f?style=flat-square"></a>
  <a href="#automation-modes"><img alt="Automation Modes" src="https://img.shields.io/badge/%F0%9F%A7%A9-automation%20modes-ff6b35?style=flat-square"></a>
  <a href="#exports"><img alt="Exports" src="https://img.shields.io/badge/%F0%9F%93%A6-exports-3776AB?style=flat-square"></a>
</p>

## Features

- Collects Cloudflare **Account ID** from an existing API token.
- Verifies token status through Cloudflare's official API.
- Tests Workers AI access against a real model endpoint.
- Exports clean JSON and CSV rows for downstream routing or manual injection.
- Supports single token, token file, and `CF_API_TOKEN` environment variable.
- Documents full automation requirements without pretending Cloudflare signup has a public API.
- No Playwright, Puppeteer, Selenium, or full browser runtime.

## Quick Start

```bash
git clone https://github.com/mocasus/Auto-FreeCF.git
cd Auto-FreeCF
python3 -m venv venv
venv/bin/pip install -e .
```

Run with one token:

```bash
CF_API_TOKEN='YOUR_CLOUDFLARE_WORKERS_AI_TOKEN' auto-freecf
```

Run with many tokens:

```bash
printf '%s\n' 'TOKEN_1' 'TOKEN_2' > tokens.txt
auto-freecf --token-file tokens.txt
```

Skip live Workers AI model test:

```bash
auto-freecf --token-file tokens.txt --no-test
```

## Automation Modes

Auto-FreeCF is explicit about what each mode can and cannot do.

**Mode: `manual-token`**

Implemented now. You manually create or paste a Cloudflare Workers AI token, then the tool extracts and verifies:

- user email, when token permission allows it
- account name
- account ID
- Workers AI access status
- token-to-account mapping

```bash
auto-freecf --mode manual-token --token-file tokens.txt
```

**Mode: `session-import`**

Design path for full automation without full browser runtime. Required inputs:

- logged-in Cloudflare dashboard session cookie exported from your own browser or phone
- CSRF/session headers captured from the dashboard
- HTTP client with browser TLS fingerprinting, such as `curl_cffi`

This mode can automate dashboard API actions after you provide an authenticated session. It avoids driving a browser, but still requires a legitimate login session.

**Mode: `solver-assisted`**

Design path for account creation from zero. Required components:

- residential or mobile IP pool
- Cloudflare managed-challenge clearance provider
- Turnstile solver, when the flow exposes a widget token
- temp-mail inbox with verification link extraction
- retry limits and cooldown logic

Cloudflare's dashboard signup is protected by Cloudflare Managed Challenge. There is no public API for creating new dashboard users from zero. Pure HTTP from a VPS receives `403 Just a moment...` before the normal signup flow.

Print requirements:

```bash
auto-freecf --print-full-auto-requirements
```

## Exports

Default output files:

```text
exports/workers_ai_accounts.json
exports/workers_ai_accounts.csv
```

Example row:

```json
{
  "email": "account@example.com",
  "account_id": "023e105f4ecef8ad9ca31a8372d0c353",
  "account_name": "example@example.com's Account",
  "api_token": "...",
  "workers_ai_ok": true,
  "workers_ai_error": null
}
```

## Workers AI Test

The default test calls:

```text
POST /client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct
```

Change model:

```bash
auto-freecf --token-file tokens.txt --model '@cf/qwen/qwen2.5-coder-32b-instruct'
```

## Token Permissions

Create a Cloudflare API token from the dashboard with Workers AI permission for the target account. If `workers_ai_ok` is false, recreate the token with the correct Workers AI scope.

## Root Cause Notes

Observed from VPS:

```text
GET https://dash.cloudflare.com/sign-up
status: 403
title: Just a moment...
cf_clearance: false
```

This means the blocker is Cloudflare's own managed challenge on the dashboard, not a normal public API error. Official Cloudflare docs also state API token creation by API requires an existing token with token-creation permission.

## CLI

```bash
auto-freecf --help
```

Important options:

```text
--token TOKEN
--token-file tokens.txt
--mode manual-token|session-import|solver-assisted
--model @cf/...
--no-test
--out-json path.json
--out-csv path.csv
```

## License

MIT

<p align="center"><sub>v1.0.0 · 2026 · Built by <a href="https://github.com/mocasus">@mocasus</a></sub></p>
