# Auto-FreeCF

Auto-FreeCF memiliki dua stack otomatisasi Cloudflare Workers AI yang berbeda:

- **Pipeline aktif:** `signup_from_scratch/` bersama `mail-adapter/` membuat akun, memverifikasi email, membuat token Workers AI, lalu memvalidasinya.
- **Stack legacy:** root `src/`, `bot.py`, `browser_bot.py`, `web_ui.py`, `terminal_ui.py`, dan CLI `moycf` menangani akun yang sudah ada. Bagian ini masih disertakan untuk kompatibilitas, tetapi bukan area utama untuk pekerjaan baru.

Gunakan perangkat lunak ini hanya untuk akun, infrastruktur email, dan otomatisasi yang memang Anda berwenang gunakan; patuhi ketentuan layanan serta hukum setempat.

## Mulai dari sini

Untuk arsitektur dan aturan proyek terkini, baca berurutan:

1. [AGENTS.md](AGENTS.md) — sumber kebenaran operasi harian dan konvensi proyek.
2. [Project guide](docs/PROJECT_GUIDE.md) — arsitektur, interface, perintah verifikasi, dan handoff agent.
3. [Signup pipeline README](signup_from_scratch/README.md) — setup serta referensi CLI pipeline aktif.
4. [Legacy refactoring note](docs/REFACTORING.md) — konteks historis saja, bukan panduan pipeline aktif.

## Pipeline aktif secara singkat

```text
mail-adapter atau mail API kompatibel
  -> alamat email sementara
  -> signup Cloudflare dan verifikasi Turnstile (nodriver)
  -> verifikasi email dalam sesi browser yang sama
  -> pembuatan token Workers AI
  -> validasi Workers AI API
  -> signup_from_scratch/results.json
```

Jalur aktif memakai `page.verify_cf()` dari nodriver untuk Turnstile. Jangan mengembalikan coordinate click, image matching, submit-first, atau sesi browser terpisah untuk verifikasi email/token.

## Verifikasi lokal yang aman

Perintah berikut tidak memulai signup browser dan tidak memanggil backend mail:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest signup_from_scratch.tests.test_proxy_manager -v
python -m unittest mail-adapter.tests.test_adapter -v
python .\signup_from_scratch\main.py --help
```

## Keamanan dan state lokal

Anggap `config.json`, `results.json`, `keys.txt`, daftar proxy, JWT mailbox, token Cloudflare, dan mapping mail-adapter sebagai rahasia. Jangan menyalin isinya ke issue, log, commit, atau dokumentasi. Lihat [SECURITY.md](SECURITY.md) dan bagian security pada [project guide](docs/PROJECT_GUIDE.md).

## Kepemilikan dokumentasi

Perbarui `AGENTS.md`, `docs/PROJECT_GUIDE.md`, dan README komponen terkait bila perubahan memengaruhi pipeline aktif, konfigurasi, interface, dependensi, tes, atau blocker operasional.