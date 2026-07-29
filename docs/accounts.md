# OpenMaster accounts and project isolation

## Purpose

Accounts replace the browser-facing shared studio password. Registration creates a
pending request; an administrator must approve it before login can create a private
workspace. Sources, analysis, settings, renders, previews, and downloads are isolated
from every other user.

## HTTP contract

All routes are same-origin under `/api/v1/auth`:

- `POST /register` accepts `display_name`, `email`, and `password`, then returns a
  pending profile without a cookie;
- `POST /login` accepts `email` and `password`;
- `GET /me` resolves the current session;
- `POST /logout` revokes the current session.

Administrator-only routes are `GET /admin/requests`,
`POST /admin/requests/{user_id}/approve`, and
`POST /admin/requests/{user_id}/reject`.

Registration and login return only the public user profile. The session token is never
included in JSON or made available to browser JavaScript.

## Administrator bootstrap

The API refuses to start without `OPENMASTER_ADMIN_EMAIL` and
`OPENMASTER_ADMIN_PASSWORD`. During startup it idempotently creates or promotes that
identity with role `admin`, status `active`, and the display name from
`OPENMASTER_ADMIN_DISPLAY_NAME`. Reapplying the deployment rotates the administrator
password to the current secret value. Concurrent API replicas are safe because the
normalized email is unique.

The email and password belong in the existing Kubernetes Secret/Vault record. The
display name is non-sensitive Helm configuration. No administrator credential is
stored in Git or rendered into the ConfigMap.

## Password storage

Emails are trimmed and case-folded before their unique constraint is evaluated.
Passwords must contain 10–128 characters. Each password receives a random 128-bit salt
and is derived with PBKDF2-HMAC-SHA256 using 600,000 iterations. PostgreSQL stores the
algorithm, iteration count, salt, and derived value; it never stores the password.
Invalid login responses do not disclose whether the email exists. After a correct
password, pending and rejected users receive their approval state so the interface can
explain why access remains unavailable.

## Sessions

A successful login creates 32 random bytes and returns their URL-safe representation
only in the `openmaster_session` cookie. PostgreSQL stores its SHA-256 digest. The
cookie is `HttpOnly`, `Secure`, `SameSite=Strict`, and scoped to `/`. The default
lifetime is 30 days and may be changed between 1 and 365 days with
`AUTH_SESSION_DAYS`. Expired sessions are removed during authentication; logout deletes
the active digest immediately.

Production must keep `AUTH_COOKIE_SECURE=true`. A developer using plain local HTTP may
set it to `false`; that setting must not be used on an Internet-facing deployment.

## Ownership

Alembic revision `0012` adds `analysis_jobs.user_id`. Every user-facing project query
includes that identifier in SQL. This applies to:

- the twenty-project history;
- polling and renaming;
- interactive settings and mastering requests;
- retained source and master previews;
- final downloads.

Background workers still resolve a queued UUID internally and do not act as a browser
user. Rows created before revision `0012` retain a null owner so the migration is safe;
they are invisible to all accounts. Assigning legacy projects, deleting accounts,
password recovery, email verification, and multiple administrator roles are
intentionally not exposed in this first account contract.

## Operational checks

After deployment:

1. confirm the migration job reports revision `0012`;
2. sign in with the bootstrapped administrator;
3. register two test accounts and approve them from the Admin page;
4. upload one source from the first account;
5. verify the second account receives `404` for that project UUID;
6. log out and verify `/api/v1/auth/me` returns `401`;
7. inspect the cookie flags without logging its value.

Never log passwords, clear session tokens, or signed MinIO URLs.
