# Auto-FreeCF Project Guide

Dokumen ini adalah panduan handoff yang tahan konteks untuk keadaan repository saat ini. Dokumen ini melengkapi `AGENTS.md`; jika ada konflik, kode dan `AGENTS.md` adalah otoritas lalu perbarui panduan ini dalam perubahan yang sama.

## Scope dan kepemilikan

| Area | Status | Fungsi |
| --- | --- | --- |
| `signup_from_scratch/` | Aktif | Pipeline pembuatan akun dan validasi token. |
| `mail-adapter/` | Aktif | Bridge HTTP lokal dari backend temp-mail ke kontrak mail pipeline. |
| Root `src/`, wrapper root, UI, `cli.js` | Legacy | Login/token grabber akun existing dan compatibility surface. Jangan jadikan template pekerjaan signup baru. |
| `docs/REFACTORING.md` | Historis | Catatan refactor login legacy, bukan arsitektur saat ini. |

## Arsitektur aktif

```text
main.py
  -> EmailGenerator              POST mail-api/new_address
  -> signup_flow.signup          Signup Cloudflare dan Turnstile
  -> email_verifier              Poll mail API dan buka link verifikasi
  -> token_creator               API-first, UI fallback jika email terverifikasi
  -> token_validator             Endpoint Workers AI models
  -> results.json                Output lokal rahasia

mail-adapter/adapter.py
  -> backend temp-mail kompatibel Supabase
  -> kontrak HTTP lokal untuk EmailGenerator dan email_verifier
```

`main.create_account` sengaja memakai ulang satu halaman browser dari signup sampai verifikasi email serta token. Browser atau tab baru dapat kehilangan sesi terautentikasi; jangan diubah tanpa keputusan desain eksplisit.

## Kontrak pipeline

1. `EmailGenerator` meminta alamat sementara melalui `mail_api`, dengan fallback relay opsional.
2. `signup_flow` mengisi kredensial, mendeteksi Turnstile, lalu memakai nodriver `page.verify_cf()` (satu retry) sebelum submit.
3. `email_verifier` mem-poll inbox dengan JWT mailbox dan membuka link verifikasi Cloudflare pada halaman yang sama.
4. Bila email terverifikasi, `main.create_account` mencoba `create_token_api` lalu fallback ke `create_token`. Bila gagal verifikasi, langsung memakai `create_token`.
5. `token_validator` memvalidasi token terhadap Workers AI dan hasil ditambahkan ke output JSON.

| Status hasil | Makna |
| --- | --- |
| `full` | Signup selesai dan token Workers AI tervalidasi. |
| `signup_only` | Account ID didapat, tetapi validasi token belum tuntas. |
| `error` | Percobaan pipeline tidak selesai. |

Result dapat memuat email, password, JWT mailbox, account ID, API token, detail validasi, status verifikasi, timestamp, dan proxy. Semua itu adalah state lokal rahasia.

## Interface mail adapter

`mail-adapter/adapter.py` membaca konfigurasi runtime dari environment, bukan dari JSON example:

| Variabel | Default | Fungsi |
| --- | --- | --- |
| `API_BASE` | Endpoint backend bawaan | Base endpoint backend temp-mail. |
| `TMK_KEY` | Fallback bawaan saat ini | API key backend. Tetapkan eksplisit pada environment; jangan dokumentasikan atau commit nilainya. |
| `PORT` | `9877` | Port listener lokal. |

| Method | Route | Autentikasi | Fungsi |
| --- | --- | --- | --- |
| POST | `/new_address` atau `/api/new_address` | Tidak ada | Membuat alamat; body berisi `domain`. |
| GET | `/parsed_mails` atau `/api/parsed_mails` | `Authorization: Bearer <jwt>` | Daftar email yang sudah dinormalisasi. |
| GET | `/domains` atau `/api/domains` | Tidak ada | Daftar domain tersedia. |

Adapter mengembalikan JWT mailbox dalam format `owner_token::address`. File runtime `mail-adapter/token_map.json` juga sensitif dan bukan material source control.

## Batas keamanan

Semua hasil pipeline adalah data lokal sensitif: termasuk password, token, JWT mailbox, proxy credentials, dan mapping adapter. Jangan commit, publish, atau masukkan ke log/dokumentasi. Jika ada rahasia terpapar, rotasi dahulu lalu ikuti [SECURITY.md](../SECURITY.md).
## Konfigurasi dan perintah

Gunakan `signup_from_scratch/config.example.json` sebagai titik awal non-rahasia. Default mencakup endpoint mail lokal, browser visible (`headless: false`), retry, delay, timeout polling, serta output file.

Sebelum perintah Python di Windows:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
```

Verifikasi aman:

```powershell
python -m unittest signup_from_scratch.tests.test_proxy_manager -v
python -m unittest mail-adapter.tests.test_adapter -v
python .\signup_from_scratch\main.py --help
```

CLI aktif menerima `--accounts`, `--config`, `--proxy`, `--output`, `--delay`, `--headless`, `--validate-only`, `--token`, `--account-id`, `--retry`, `--workers`, `--no-dashboard`, dan `--export-txt`. Gunakan `python .\signup_from_scratch\main.py --help` sebagai kontrak executable.

Run operasional yang panjang harus berjalan di background dengan stdout/stderr menuju log bernama; jangan memblokir sesi agent interaktif. Saat browser aktif, minimize (bukan hidden) agar user tetap dapat melihatnya.

## Tes dan batas verifikasi

| Tes | Cakupan | Layanan eksternal/browser |
| --- | --- | --- |
| `signup_from_scratch.tests.test_proxy_manager` | Parsing proxy dan rotasi pool | Tidak ada |
| `mail-adapter.tests.test_adapter` | Route, autentikasi, normalisasi email | Mocked |

Belum ada tes end-to-end signup otomatis yang terdokumentasi. Run signup nyata adalah validasi operasional yang bergantung pada otorisasi, rate limit Cloudflare, kualitas proxy, dan ketersediaan mail provider.

## Kendala operasional yang diketahui

- Rate limit Cloudflare serta reputasi IP adalah bottleneck utama; tunggu atau gunakan proxy fresh yang diizinkan saat terjadi.
- Jalur Turnstile aktif hanya nodriver `page.verify_cf()`.
- Jika `mail_api` mengarah ke `localhost:9877`, adapter harus berjalan; connection refused berarti adapter tidak tersedia atau endpoint salah.
- Concurrent worker berbagi nilai proxy yang dikonfigurasi. CLI tidak membagi proxy unik per worker.
- `signup_from_scratch/batch_run.py` adalah helper sequential terpisah yang memakai satu proxy per akun dan parameter hard-coded; bukan main CLI.

## Checklist pemeliharaan dokumentasi

Untuk perubahan signifikan, perbarui dalam patch yang sama:

- `AGENTS.md` untuk perilaku operasi, perubahan modul, default konfigurasi, blocker, dependensi, atau layout tes.
- Panduan ini untuk arsitektur, kontrak, perintah, dan konteks handoff.
- `signup_from_scratch/README.md` atau dokumentasi komponen untuk setup serta CLI yang user-facing.
- ADR di `docs/decisions/` hanya untuk keputusan teknis konsekuensial yang mahal dibalikkan.

## Gap terverifikasi (2026-07-16)

1. Workflow GitHub Actions merujuk path package `auto_freecf` yang tidak ada. Workflow tersebut belum menjadi sinyal verifikasi valid untuk pipeline aktif hingga diperbaiki.
2. `signup_from_scratch/.gitignore` memakai pola yang tampak root-relative, padahal Git menafsirkannya relatif terhadap subdirektori. Status repository membuktikan file generated sensitif dapat tidak ter-ignore. Jangan stage file itu; perbaiki ignore rules sebagai perubahan security/konfigurasi tersendiri.
3. Mail adapter saat ini memiliki fallback credential backend di kode. Dokumentasi mengarahkan konfigurasi environment, tetapi menghapus fallback adalah perubahan keamanan pada kode dan sengaja di luar audit dokumentasi ini.