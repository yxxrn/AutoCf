# Security Policy

## Supported scope

Security fixes and reports are evaluated against the current `main` branch, especially the active `signup_from_scratch/` and `mail-adapter/` pipeline. Historical versions and the legacy login stack may receive compatibility fixes at maintainer discretion; do not rely on the version table in older documentation.

## Sensitive local state

Never commit, publish, or paste any of the following into issues, logs, screenshots, or documentation:

- Cloudflare API tokens, account IDs paired with tokens, passwords, or browser session data.
- Temporary-mail JWTs, owner tokens, message contents, backend API keys, or `mail-adapter/token_map.json`.
- `config.json`, `results.json`, `keys.txt`, proxy credentials, proxy lists, and runtime logs.

If a secret is exposed, revoke or rotate it with the relevant provider first. Then remove it from accessible artifacts and report the exposure privately.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to [andikastore.ads@gmail.com](mailto:andikastore.ads@gmail.com). Include:

1. A concise description of the impact.
2. A minimal reproduction that does not contain valid credentials or tokens.
3. Affected file, component, and revision if known.
4. Any mitigation already applied, such as token rotation.

Do not open a public issue containing exploit details, secrets, or personal data. Do not test against accounts or infrastructure you do not own or have permission to assess.

## In scope

- Accidental exposure or unsafe storage of credentials, tokens, mailbox data, proxy credentials, or configuration.
- Authorization and authentication weaknesses in the local mail adapter.
- Dependency vulnerabilities affecting the shipped Python or Node components.
- Browser-automation behavior that leaks local secrets or bypasses an authorization boundary.

## Out of scope

- Availability or policy decisions of Cloudflare, Google, Supabase, or other third-party services.
- Rate limits, anti-abuse challenges, and ordinary user configuration errors.
- Reports without a reproducible security impact.

## Maintainer response target

Maintainers aim to acknowledge a report within 48 hours, provide a status update within 7 days, and coordinate disclosure after a fix is available. These are targets, not a service-level guarantee.