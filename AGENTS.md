# AGENTS.md — Auto-FreeCF

> Baca ini di awal setiap sesi. Semua konteks proyek ada di sini.

---

## 0. Aturan Kerja

1. **Bahasa Indonesia** saat komunikasi dengan user.
2. **Update dokumen** setiap ada perubahan signifikan (§5).
3. **Run panjang di background**, log ke file. Jangan blocking.
4. **Browser minimize** (bukan hidden) — user pakai layar bersamaan.
5. Jangan commit/push kecuali diminta eksplisit.
6. Error encoding Windows → selalu set `PYTHONIOENCODING=utf-8` sebelum run.

### Peta dokumentasi

- `AGENTS.md` ini: source of truth untuk operasi dan aturan agent.
- `docs/PROJECT_GUIDE.md`: handoff arsitektur, kontrak interface, perintah verifikasi, dan gap yang telah diaudit.
- `signup_from_scratch/README.md`: setup serta referensi CLI pipeline aktif.
- `docs/REFACTORING.md`: sejarah stack login legacy; jangan dipakai sebagai panduan pipeline aktif.

---

## 1. Proyek Overview

**Auto-FreeCF** — otomatisasi pembuatan akun Cloudflare + Workers AI token.

### Source of truth (pipeline aktif)

| Direktori | Fungsi |
|---|---|
| `signup_from_scratch/` | **Pipeline utama** signup → verify email → token → validate |
| `mail-adapter/` | Bridge Supabase temp-mail API → format yang dipakai generator |

### Legacy (masih di-ship, bukan fokus)

| Path | Fungsi |
|---|---|
| `src/browser_bot.py`, `bot.py`, `browser_bot.py` | Login grabber (akun existing) via Patchright |
| `web_ui.py`, `terminal_ui.py`, `cli.js` | UI/CLI wrapper npm (`moycf`) |
| `docs/REFACTORING.md` | Catatan refactor **legacy** login stack (bukan signup) |

### Pipeline (`signup_from_scratch`)

```
1. Buat email temp        → src/email_generator.py
2. Signup Cloudflare      → src/signup_flow.py  [Turnstile: verify_cf() nodriver]
3. Verifikasi email CF     → src/email_verifier.py
4. Buat API token         → src/token_creator.py  (API dulu, UI fallback)
5. Validasi token         → src/token_validator.py
6. Simpan results.json    → {email, account_id, api_token, token_valid, ...}
```

**Modul pendukung (dipakai pipeline):**

| File | Peran |
|---|---|
| `src/turnstile_bypass.py` | `verify_cf`, `is_turnstile_present` saja |
| `src/humanize.py` | `human_type` / `human_click` |
| `src/proxy_manager.py` | parse proxy + CDP proxy auth |
| `src/stealth.py` | `USER_AGENTS` (+ helper fingerprint; `apply_stealth` tersedia) |
| `src/live_dashboard.py` | Rich dashboard opsional |
| `src/utils.py` | config, save results, password/username |
| `batch_run.py` | batch: 1 proxy = 1 akun |
| `src/proxy_cf_tester.py` | util filter proxy vs CF (standalone) |

**Modul yang dihapus (orphan, 2026-07-14):**  
`js_challenge_bypass.py`, `turnstile_solver_pw.py` — tidak diimport pipeline; OpenCV/Pillow tidak lagi di `requirements.txt`.

**Output**: `signup_from_scratch/results.json`

```json
{
  "email": "user@domain.com",
  "password": "...",
  "account_id": "fd2a42f35c5637a94b0f9223c07d74b4",
  "api_token": "cfut_...",
  "token_valid": true,
  "workers_ai_models": 61,
  "status": "full",
  "created_at": "2026-07-11T16:27:00+00:00"
}
```

---

## 2. Konfigurasi

### signup_from_scratch/config.json

Salin dari `config.example.json`. Contoh minimal:

```json
{
  "mail_api": "http://localhost:9877/new_address",
  "mail_fallback": "",
  "mail_domains": ["moymoy.me", "moyqris.me", "kintole.com", "gmilio.web.id"],
  "proxy": null,
  "headless": false,
  "max_accounts": 10,
  "delay_between_accounts": 60,
  "retry_attempts": 3,
  "token_name": "workers-ai-auto",
  "output_file": "results.json",
  "email_verify_timeout": 120,
  "email_verify_poll_interval": 5
}
```

Catatan:

- `mail_fallback` kosong disarankan agar tidak double-fail ke localhost mati.
- `email_generator` juga punya `PUBLIC_RELAY` hardcoded sebagai tier terakhir (bisa mati kapan saja).

### mail-adapter

`adapter.py` membaca env (bukan `config.json` saat ini):

| Env | Default | Arti |
|---|---|---|
| `API_BASE` | URL Supabase temp-mail edge function | Backend |
| `TMK_KEY` | (lihat source / set sendiri) | Header `x-api-key` |
| `PORT` | `9877` | Listen port |

Jangan commit API key nyata. Template: `mail-adapter/config.example.json` (placeholder only).

---

## 3. Cara Run

### 1. Start Mail Adapter (WAJIB untuk self-host)

```bash
# Terminal 1
cd B:/Project/Auto-FreeCF/mail-adapter
# Opsional: set TMK_KEY / API_BASE
python adapter.py

# Test
curl -X POST http://localhost:9877/new_address \
  -H "Content-Type: application/json" \
  -d "{\"domain\":\"gmilio.web.id\"}"
# Expected: {"address":"...@gmilio.web.id","jwt":"owner::address",...}
```

Adapter path yang didukung: `POST /new_address` **dan** `POST /api/new_address`.

### 2. Run Signup

```bash
# Terminal 2
cd B:/Project/Auto-FreeCF/signup_from_scratch

# Set encoding dulu (WAJIB di Windows)
set PYTHONIOENCODING=utf-8

# 1 akun (test)
python main.py --accounts 1

# N akun
python main.py --accounts 10

# Headless
python main.py --accounts 5 --headless

# Dengan proxy
python main.py --accounts 5 -p "http://user:pass@host:port"

# Validate token existing
python main.py --validate-only --token cfut_xxx --account-id abc123
```

### 3. Unit tests (tanpa browser / tanpa Supabase)

```bash
# Proxy parser
cd B:/Project/Auto-FreeCF/signup_from_scratch
python -m unittest tests.test_proxy_manager -v

# Mail adapter normalize + routes (mock)
cd B:/Project/Auto-FreeCF/mail-adapter
python -m unittest tests.test_adapter -v
```

### 4. Cek Results

```powershell
Get-Content "B:\Project\Auto-FreeCF\signup_from_scratch\results.json" -Raw

$d = Get-Content "B:\Project\Auto-FreeCF\signup_from_scratch\results.json" -Raw | ConvertFrom-Json
($d | Where-Object { $_.token_valid -eq $true }).Count
```

### 5. Validate Token via API

```bash
curl "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search" \
  -H "Authorization: Bearer {api_token}"
```

---

## 4. Jebakan yang Sudah Diketahui

| Gejala | Penyebab | Solusi |
|---|---|---|
| `UnicodeEncodeError: charmap` | Emoji/Unicode di Windows console cp1252 | Set `PYTHONIOENCODING=utf-8` |
| `All mail relays failed / connection refused` | Mail adapter tidak running atau URL mati | Start `mail-adapter/adapter.py`; cek `mail_api` di config |
| `/new_address` → `{"error":"Not found"}` | Adapter path mismatch / process lama | Pastikan adapter terbaru di port 9877; test `curl` |
| `connection refused` di mail adapter | Port 9877 sudah dipakai process lain | `netstat -ano` cari `:9877`, kill process lama |
| Turnstile failed | IP rate limit CF atau proxy mati | Tunggu 2-6 jam, atau proxy residential fresh |
| `email_not_verified` saat create token | Email belum verify / race | Pipeline retry settle; cek inbox via adapter |
| nodriver browser crash | Memory/sandbox issue | Run dengan `sandbox=False` (sudah default di main) |
| `verify_cf returned empty Turnstile token` | Challenge tidak resolve | Ganti IP/proxy, retry |

---

## 5. Kapan Update Dokumen

Update dokumen jika ada perubahan pada:

- Alur pipeline signup / Turnstile / token
- Tambah / hapus file di `signup_from_scratch/src/`
- Konfigurasi default (`config.json`, `config.example.json`)
- Blockers atau status proyek
- Keputusan teknis baru
- Dependencies / test layout
- Kontrak mail adapter atau output result
- Catatan handoff/known gap yang dapat memengaruhi agent berikutnya

---

## 6. Arsitektur Kunci

### Turnstile Bypass

Hanya satu cara yang work: `page.verify_cf()` dari nodriver.

- File: `src/turnstile_bypass.py` — `verify_cf`, `is_turnstile_present`
- **Jangan** pakai: OS-click coordinate, OpenCV template matching, submit-first, patchright isolated solver

### Email Flow

```
email_generator.py  → POST mail_api/new_address → {email, jwt}
email_verifier.py   → poll /parsed_mails, buka link verify CF di page yang sama
mail-adapter        → Supabase create/messages ↔ format bluk-cf
```

JWT dari adapter: `owner_token::address` (Bearer).

### Token Creation

Di **`main.create_account`** (source of truth):

1. Jika email verify **sukses** → `create_token_api` dulu → fallback `create_token` (UI lalu API)
2. Jika email verify **gagal** → langsung `create_token` (UI path)

Permissions: Workers AI Read (`a92d2450e05d4e7bb7d0a64968f83d11`) + Write (`bacc64e0f6c34fc0883a1223f938a104`).

### Browser Session

Reuse `page` yang sama dari signup untuk verify + token.  
Jangan buka browser/tab baru — session state hilang.

### Proxy

- Parse: `user:pass@host:port`, `host:port:user:pass`, scheme `http://` / `socks4://` / `socks5://` di-strip
- Auth: `attach_proxy_auth()` via CDP Fetch **setelah** navigasi pertama

---

## 7. Catatan History Fix

### 2026-07-11 s/d 2026-07-12

- Sync signup + turnstile ke pattern bluk-cf (working)
- Hapus submit-first / OS-click / complex retry
- Adapter path `/new_address` + `/api/new_address`
- Fix port 9877 process stuck, Unicode Windows, `mail_fallback` kosong
- Label log ASCII (`[ok]`, `[err]`, `[warn]`)
- Humanize input, proxy auth CDP, fingerprint/UA random
- Batch: 1 proxy = 1 akun; `proxy_cf_tester.py`
- **Hasil:** 5 akun valid dari ~22 percobaan; bottleneck = rate limit IP

### 2026-07-14 — docs sync + cleanup

- Hapus orphan: `js_challenge_bypass.py`, `turnstile_solver_pw.py`
- Requirements signup: drop OpenCV/Pillow/numpy; keep nodriver, httpx, rich, curl_cffi (opsional proxy check)
- Unit test: `signup_from_scratch/tests/test_proxy_manager.py`, `mail-adapter/tests/test_adapter.py`
- Sinkron AGENTS + README dengan kode nyata (Turnstile, token order, legacy vs aktif)
- `verify_cf` raise jika token kosong; fix log/docstring token creator

### Status

- Pipeline ready untuk run dengan **IP/proxy fresh**
- Rate limit CF tetap bottleneck utama setelah beberapa signup
