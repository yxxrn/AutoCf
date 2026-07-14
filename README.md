<div align="center">

# 🚀 Auto-FreeCF

<img src="assets/logo.svg" alt="Auto-FreeCF Logo" width="200"/>

### Cloudflare Workers AI Account ID & Token Auto-Grabber

<img alt="Version" src="https://img.shields.io/badge/version-v4.3.1-5865F2?style=flat-square">
<img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square">
<img alt="Node" src="https://img.shields.io/badge/node-%3E=18.0.0-339933?style=flat-square">
<img alt="Python" src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square">
<img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square">

**Fully automated Cloudflare account grabber with advanced stealth scripts**

[Installation](#-installation) • [Usage](#-usage) • [Features](#-features) • [Documentation](#-documentation)

</div>

---

## ⚡ Quick Start

```bash
npm install -g auto-freecf
moycf
```

---

## ✨ Features

- 🤖 **Full Automation** — Login, grab Account ID, create API Token, all automatic
- 🛡️ **Stealth Mode** — Bypass Cloudflare bot detection with advanced stealth scripts
- 👻 **Headless by Default** — Runs completely in background, no browser window opens
- 🌐 **Residential Proxy** — Optional proxy configuration for better success rate
- 📝 **Single & Bulk** — Input single email:pass atau bulk dari file
- 📦 **Auto Setup** — Automatic dependency installation with live timer
- 💾 **Export Results** — Save to TXT format with account_id:worker_token
- 🔐 **Google OAuth** — Support login via Google Sign-In (fully automated)

---

## 📁 Project Structure

```
Auto-FreeCF/
├── signup_from_scratch/    # ★ ACTIVE: signup from zero → Workers AI token
│   ├── main.py             # Orchestrator
│   ├── tests/              # Unit tests (proxy parser, no browser)
│   ├── src/
│   │   ├── signup_flow.py      # CF signup + Turnstile (nodriver verify_cf)
│   │   ├── turnstile_bypass.py # verify_cf + is_turnstile_present only
│   │   ├── email_generator.py
│   │   ├── email_verifier.py
│   │   ├── token_creator.py    # API first (from main), UI fallback
│   │   ├── token_validator.py
│   │   ├── humanize.py
│   │   ├── proxy_manager.py
│   │   └── utils.py
│   └── config.example.json
├── mail-adapter/           # Temp-mail bridge (Supabase → local HTTP)
│   ├── adapter.py
│   ├── tests/
│   └── config.example.json
├── src/                    # LEGACY: login grabber (existing accounts)
│   ├── browser_bot.py
│   ├── turnstile_solver.py
│   └── utils.py
├── cli.js                  # npm CLI (moycf)
├── browser_bot.py          # Legacy wrapper
├── web_ui.py / terminal_ui.py
├── AGENTS.md               # Ops context for agents (source of truth)
└── package.json
```

## 🚀 Installation

```bash
npm install -g auto-freecf
```

## 💻 Usage

### CLI Mode

```bash
# Single account (email:password)
moycf email@example.com:password123

# Bulk accounts from file
moycf accounts.txt

# With proxy
moycf accounts.txt --proxy config/proxy.json

# Google OAuth login
moycf google_email:password --login-method google
```

### Interactive Mode

```bash
moycf
```

Then choose:
1. Single account (email:password)
2. Single account (Google OAuth)
3. Bulk accounts (from file)

### Web UI

```bash
python web_ui.py
```

Open http://localhost:8080 in your browser.

### 🔥 Signup From Scratch (NEW)

Create Cloudflare accounts from zero — no existing email needed:

```bash
# Interactive mode (recommended)
moycf
# → Pick [4] Signup from scratch
# → Pick [1] Public relay (zero setup) or [2] Custom mail API

# Direct CLI
moycf --signup --accounts 3
moycf --signup --accounts 3 --mail-api https://your-relay.example.com/new_address
```

**Mail providers:**
- 🚀 **Public relay** — pre-configured, works out of the box (option `[1]`)
- 🔌 **Custom API** — point to your own mail-adapter (option `[2]`)
- 🏗️ **Deploy your own** — full guide via Supabase (option `[3]`)
- 🔄 **Auto-fallback** — if primary relay fails, tool auto-tries backup + public relay (zero config needed)

**Full pipeline:**
1. Temp-mail → 2. CF Signup (`page.verify_cf()`) → 3. Email verify → 4. API token (API then UI) → 5. Validate

**Output:** JSON objects in `signup_from_scratch/results.json` (`email`, `account_id`, `api_token`, `token_valid`, …).

**Docs:** day-to-day ops → [`AGENTS.md`](AGENTS.md) · pipeline detail → [`signup_from_scratch/README.md`](signup_from_scratch/README.md)

### VPS Deployment

```bash
./deploy-browserfarm.sh
```

## 🔧 Development

### Active vs legacy

| Area | Path | Notes |
|------|------|--------|
| **Active pipeline** | `signup_from_scratch/` + `mail-adapter/` | Signup from zero; maintained |
| **Legacy login** | `src/browser_bot.py`, `bot.py`, UI wrappers | Existing email:pass grabber |
| **Agent ops doc** | `AGENTS.md` | Update on every significant pipeline change |

Turnstile on the **active** path uses only nodriver `verify_cf()` — not OpenCV / coordinate click.

### Unit tests (no browser)

```bash
cd signup_from_scratch
python -m unittest tests.test_proxy_manager -v

cd ../mail-adapter
python -m unittest tests.test_adapter -v
```

### Manual / legacy smoke

```bash
# Legacy login helper (needs credentials)
python browser_bot.py --help
```

## 🔒 Security

See [SECURITY.md](SECURITY.md) for details on reporting vulnerabilities and security best practices.

---

## 📜 Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for our community guidelines and standards.

---

## 📝 License

MIT
