# Cloudflare Auto Signup (`signup_from_scratch`)

Pipeline aktif Auto-FreeCF: buat akun Cloudflare dari nol + Workers AI API token.

> Untuk konteks agent/ops harian, baca juga root [`AGENTS.md`](../AGENTS.md).

---

## Apa yang dilakukan tool ini

1. Generate temp email (via mail-adapter / relay)
2. Signup Cloudflare (form + Turnstile via nodriver `verify_cf()`)
3. Verifikasi email dari inbox temp
4. Buat Account API Token (Workers AI Read + Write)
5. Validasi token ke API Workers AI
6. Simpan ke `results.json` (+ opsional export TXT 9Router)

Contoh output:

```json
{
  "email": "cf12345@yourdomain.com",
  "password": "...",
  "account_id": "a1b2c3d4e5f6789012345678abcdef01",
  "api_token": "cfut_xxxxxxxx",
  "token_valid": true,
  "workers_ai_models": 61,
  "token_name": "workers-ai-auto",
  "status": "full",
  "created_at": "2026-07-11T16:27:00+00:00",
  "proxy_used": "direct"
}
```

---

## Tools & stack (aktual)

| Tool | Purpose |
|------|---------|
| [nodriver](https://github.com/ultrafunkamsterdam/nodriver) | Chrome automation + `page.verify_cf()` |
| [httpx](https://www.python-httpx.org/) | Mail API + (via module) HTTP |
| [rich](https://github.com/Textualize/rich) | Live dashboard opsional |
| curl_cffi (opsional) | Live-check proxy di `proxy_manager` |
| Google Chrome | Browser engine |

**Turnstile (Juli 2026):** hanya `await page.verify_cf()`.  
Tidak memakai OpenCV, template matching, OS-click, atau submit-first.

Alur singkat di `signup_flow.py`:

1. Isi email/password dengan `human_type`
2. Deteksi widget (`is_turnstile_present`)
3. `verify_cf` (+ 1x retry)
4. Submit + ambil `account_id` dari URL redirect

---

## Requirements

- Python 3.10+
- Google Chrome (stable)
- Windows / Linux / macOS (Linux VPS: disarankan Xvfb jika headless tanpa display)
- Mail adapter running **atau** mail API kompatibel

```bash
pip install -r requirements.txt
```

---

## Quick start

### 1. Mail adapter (self-host)

```bash
cd ../mail-adapter
python adapter.py
# listens :9877 — POST /new_address
```

### 2. Config

```bash
cp config.example.json config.json
# edit mail_api, mail_domains, proxy
```

Default example mengarah ke `http://localhost:9877/new_address`.  
Biarkan `mail_fallback` kosong jika tidak punya backup relay.

### 3. Run

```bash
# Windows
set PYTHONIOENCODING=utf-8

python main.py --accounts 1
python main.py -n 5 -p "http://user:pass@host:port"
python main.py --validate-only --token cfut_xxx --account-id abc123
python main.py -n 10 --export-txt keys.txt --no-dashboard
```

### 4. Unit tests

```bash
python -m unittest tests.test_proxy_manager -v
```

---

## CLI

```
python main.py [OPTIONS]

  -n, --accounts N       Jumlah akun (default: 1)
  -c, --config FILE      Config JSON
  -p, --proxy URL        Proxy URL
  -o, --output FILE      Output JSON
  -d, --delay SECS       Delay antar akun
  --headless             Chrome headless
  --retry N              Retry per akun
  -w, --workers N        Concurrent workers (hati-hati rate limit)
  --no-dashboard         Matikan Rich dashboard
  --export-txt FILE      Export key valid format 9Router
  --validate-only        Hanya validasi token
  --token / --account-id Untuk --validate-only
```

---

## Struktur

```
signup_from_scratch/
├── main.py                 # Orchestrator
├── batch_run.py            # Batch 1-proxy-1-akun
├── config.example.json
├── requirements.txt
├── tests/
│   └── test_proxy_manager.py
└── src/
    ├── email_generator.py
    ├── email_verifier.py
    ├── signup_flow.py
    ├── turnstile_bypass.py   # verify_cf only
    ├── token_creator.py      # API + UI
    ├── token_validator.py
    ├── humanize.py
    ├── proxy_manager.py
    ├── proxy_cf_tester.py    # util standalone
    ├── stealth.py            # USER_AGENTS / fingerprint helpers
    ├── live_dashboard.py
    └── utils.py
```

---

## Token creation order

Di `main.create_account`:

1. Email verify sukses → **`create_token_api`** → fallback **`create_token`** (UI lalu API)
2. Email verify gagal → **`create_token`** saja

Permission IDs Workers AI (Read + Write) ada di `token_creator.py`.

---

## Security notes

Jangan commit:

- `config.json`, `results.json`, `keys.txt`
- proxy credentials, mailbox JWT, `cfut_` tokens

Treat `results.json` sebagai secret store lokal.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| Config not found | `cp config.example.json config.json` |
| connection refused mail | Start `mail-adapter/adapter.py`; cek `mail_api` |
| Unable to sign up | Rate limit IP — tunggu 2–6 jam atau ganti proxy |
| Turnstile failed / empty token | Proxy/IP jelek; retry dengan IP fresh |
| email_not_verified | Pastikan adapter expose `/parsed_mails` + JWT Bearer |
| UnicodeEncodeError (Windows) | `set PYTHONIOENCODING=utf-8` |

---

## Legal

Untuk automation yang diizinkan / testing / research. Patuhi ToS Cloudflare dan hukum setempat. Author tidak bertanggung jawab atas penyalahgunaan.

## License

MIT — lihat root `LICENSE`.
