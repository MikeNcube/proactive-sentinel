# Security audit: hardcoded secrets & credentials

This document captures the complete inventory of hardcoded secrets and
demo credentials found in the repository as part of the PR that
stopped tracking `.env` and scrubbed leaked defaults. It is committed
for auditability. Future audits should append new sections rather than
edit history.

---

## 1. Real secrets committed to git

These values are considered **compromised** the moment this PR merges.
They must be rotated in the production secret store (Railway / AWS /
etc.) and the old values invalidated. See "Manual rotation steps" at
the end of this document.

| Location | Key | Disposition |
|----------|-----|-------------|
| `.env` (tracked) | `ENCRYPTION_KEY` | Removed from HEAD; PURGE git history. **Rotate + re-encrypt PII.** |
| `.env` (tracked) | `BACKUP_ENCRYPTION_KEY` | Removed from HEAD; PURGE git history. Rotate. |
| `.env` (tracked) | `JWT_SECRET_KEY` | Removed from HEAD; PURGE git history. Rotate immediately. |
| `.env` (tracked) | `DASHBOARD_SECRET_KEY` | Removed from HEAD; PURGE git history. Rotate. |
| `.env` (tracked) | `POSTGRES_PASSWORD` | Removed from HEAD; PURGE git history. Rotate DB password. |

## 2. Hardcoded passwords in source

| File (before PR) | What | Now |
|------------------|------|-----|
| `fix_passwords.py` | `admin@acme.com / password123`, `admin@zororo.co.za / Admin1234!`, `test@acme.com / test123` | Reads `FIX_*_PASSWORD` from env; refuses without `ALLOW_PASSWORD_RESET=1`; blocked in `FLASK_ENV=production`. |
| `seed.py` | `admin@zororo.co.za / Admin1234!` | Reads `SEED_ADMIN_PASSWORD` from env; blocked in prod without `SEED_ALLOW_PROD=1`. |
| `seed_fix.py` | `password123` / `Admin1234!` (bcrypt seeding) | Stub that exits non-zero and points at `fix_passwords.py`. |
| `seed_fixed.py` | `password123` / `Admin1234!` (werkzeug seeding) | Stub that exits non-zero and points at `fix_passwords.py`. |
| `scripts/seed_data.py` | 5 users × `password123` / `Admin1234!` | Reads `SEED_*_PASSWORD` per user; requires `SEED_ALLOW=1`; blocked in prod. |
| `verify_docker.ps1` | `admin@zororo.co.za / Admin1234!` | Reads `$env:VERIFY_LOGIN_EMAIL` / `$env:VERIFY_LOGIN_PASSWORD`; refuses without them. |
| `init.sql` | `CREATE ROLE app_user ... PASSWORD 'app_password'` with `ALL PRIVILEGES` | Role creation removed. App connects as the compose-provisioned `sentinel` role. |
| `src/config.py` | `postgresql://sentinel:dev_password@postgres:5432/sentinel` as `TestingConfig` default | Default removed; callers must set `DATABASE_TEST_URL` or `DATABASE_URL`. |
| `scripts/setup_database.py` | `postgresql://sentinel:dev_password@postgres:5432/sentinel_test` | URL is now built from `$POSTGRES_PASSWORD`; script errors if unset. |
| `scripts/setup_windows.bat` | Same as above | Same fix. |
| `dashboard/flask_dashboard.py` | Login-form placeholder `admin@acme.com` | Placeholder changed to `you@example.com`. |

## 3. Hardcoded credentials shipped in front-end templates

The dashboard templates contained a `silentLogin()` JS function that
auto-authenticated the browser as `admin@zororo.co.za / Admin1234!`,
plus a "Risky Users" widget that hardcoded real tenant emails.

| File | Change |
|------|--------|
| `templates/dashboard.html` | `silentLogin()` now redirects to `/login`; sidebar email placeholder neutralised; `riskyUsers` widget no longer embeds emails. |
| `dashboard/templates/dashboard.html` | Same. |
| `dashboard/templates/index.html` | Same. |
| `frontend_export/dashboard.html` | Same. |
| `AI-Social-Agent/dashboard/templates/dashboard.html` | Same. |
| `AI-Social-Agent/dashboard/templates/index.html` | Same. |
| `frontend_files_for_kimi.txt` (LLM-paste dump) | Same sanitisation applied; file retained because deleting it is out of scope for this PR. |

## 4. VS Code `.history/` snapshots (AI-Social-Agent)

The following tracked files duplicated historical `.env` / docker-compose
snapshots and have been removed from the index and from the working
tree. They also existed in git history; purge separately (see manual
steps).

```
AI-Social-Agent/.history/.env_20260311172342
AI-Social-Agent/.history/.env_20260311172707
AI-Social-Agent/.history/.env_20260311172708
AI-Social-Agent/.history/.env_20260311172709
AI-Social-Agent/.history/.env_20260318192034
AI-Social-Agent/.history/.gitignore_*
AI-Social-Agent/.history/README_*
AI-Social-Agent/.history/agents/prompts/strategist_*
AI-Social-Agent/.history/docker/docker-compose_*
```

`.gitignore` now excludes `.history/` and `**/.history/` at the repo root.

## 5. Default placeholder credentials

These are not "real secrets" but are default values a user might run
unmodified. Treated with `:?` enforcement so an unset env var now
fails the start instead of silently using the placeholder.

| File | Key | Change |
|------|-----|--------|
| `AI-Social-Agent/docker/docker-compose.yml` | `N8N_BASIC_AUTH_PASSWORD=yourpassword` | `${N8N_BASIC_AUTH_PASSWORD:?N8N_BASIC_AUTH_PASSWORD must be set}` |
| `AI-Social-Agent/docker/docker-compose.yml` | `N8N_ENCRYPTION_KEY=your-encryption-key-here` | `${N8N_ENCRYPTION_KEY:?N8N_ENCRYPTION_KEY must be set}` |

## 6. Intentionally not changed (scope discipline)

- `tests/conftest.py`, `tests/integration/conftest.py`, `tests/integration/test_api_flow.py` — still reference `Admin1234!` as an in-test password. These are test-only fixtures and do not ship; moving them to pytest-generated randoms is scheduled for a follow-up PR.
- Migration files in `migrations/versions/` — matched the `secret` / `password` regex only on column names (`password_hash`, `mfa_secret_encrypted`). No secret values embedded.
- `.env.example` placeholder strings like `replace-with-random-64-hex` — these are documentation, not secrets.

---

## Manual rotation steps (operator action required)

**This PR cannot rotate live infrastructure**; operator must do the
following out-of-band after merging:

1. **Generate fresh values:**

   ```
   python scripts/rotate_secrets.py
   ```

   Do NOT paste the output into a shared chat, a screen recording, or a
   logged terminal. Copy directly into the platform's secret UI.

2. **Update Railway (or your platform) variables** to the new values:

   ```
   railway variables set JWT_SECRET_KEY=<new>
   railway variables set DASHBOARD_SECRET_KEY=<new>
   railway variables set POSTGRES_PASSWORD=<new>
   # ENCRYPTION_KEY must be rotated carefully -- see step 3.
   ```

3. **ENCRYPTION_KEY rotation (high-risk)** — rotating this key without
   re-encrypting existing PII rows will make `User.phone`,
   `User.full_name`, `User.address`, `User.mfa_secret` permanently
   undecryptable. Recommended procedure:

   1. Generate a new candidate key: `python scripts/rotate_secrets.py --only ENCRYPTION_KEY`.
   2. Set `BACKUP_ENCRYPTION_KEY = <current ENCRYPTION_KEY>` (the old key).
   3. Deploy the app with both keys active; write a one-shot script that
      decrypts each PII column using `BACKUP_ENCRYPTION_KEY` and re-encrypts
      with the new `ENCRYPTION_KEY`. (Not part of this PR.)
   4. Once re-encryption is complete, unset `BACKUP_ENCRYPTION_KEY` and
      promote the new key to `ENCRYPTION_KEY`.

   If PII re-encryption tooling is not yet built, **defer ENCRYPTION_KEY
   rotation** and instead ensure the old key is not present in any
   accessible environment. It's safer to leave a known-burned key in
   place than to brick PII decryption.

4. **Invalidate outstanding JWTs.** Rotating `JWT_SECRET_KEY`
   automatically invalidates every previously-issued token, which will
   log all users out. Coordinate with operators.

5. **Rotate the Postgres password.** Railway (or your provider) can
   rotate `DATABASE_URL` in-place. Confirm the app reconnects cleanly
   after the variable update.

6. **Purge the leaked values from git history.** The old `.env` and
   `.history/.env_*` files are still recoverable from any clone of this
   repo until history is rewritten. Use `git filter-repo`:

   ```
   pip install git-filter-repo
   git clone --mirror git@github.com:MikeNcube/proactive-sentinel.git psentinel-mirror
   cd psentinel-mirror
   git filter-repo --path .env --invert-paths
   git filter-repo --path-glob 'AI-Social-Agent/.history/*' --invert-paths
   git push --force --all
   git push --force --tags
   ```

   Every existing clone / fork / CI cache must re-clone after the
   force-push. Coordinate a window.

7. **Rotate any downstream credentials** that may have been derived
   from the leaked values (e.g., API keys issued by partners that were
   sent inside requests signed with the leaked JWT secret).
