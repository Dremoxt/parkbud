---
name: security-checklist
description: Security and compliance review criteria for this project. Use when auditing code that handles authentication, user data, external input, dependencies, or configuration.
---

# Security checklist

> The baseline below is general. The section immediately after it is what actually
> applies to this project — a static site with no backend, no accounts, and no database.

## What matters here

- **The analytics consent gate is the main control.** Nothing may load a tracker, pixel
  or third-party script before consent. Two checks guard this: `static_checks.py` asserts
  no analytics tag bypasses the gate on any page, and `tests/consent.spec.js` verifies the
  gate at runtime. Treat a failure in either as a privacy incident, never as a test to
  relax. See `docs/analytics.md`.
- **GDPR applies** — the audience is EU visitors. Collect nothing that isn't needed, and
  keep the privacy page under `privacy/` truthful about what is actually collected.
- **Outbound links go to third-party operator booking sites.** Every `target="_blank"`
  link currently carries `rel="noopener noreferrer"`, and `static_checks.py` enforces it
  per page. Don't pass visitor data in outbound URLs.
- Sections below on auth, sessions, SQL and deserialization don't currently apply — no
  such surfaces exist. If one is ever added, they do.

## Secrets
- No keys, tokens, passwords, or private keys in code, config, fixtures, or logs.
- Secrets come from environment or a secrets manager; `.env` files are gitignored.

## Input & output
- Validate and sanitize all external input at the trust boundary.
- Use parameterized queries / prepared statements — never string-concatenate into SQL or shell.
- Encode output for its context (HTML, URL, shell) to prevent injection/XSS.
- Avoid unsafe deserialization of untrusted data.

## Authentication & authorization
- Every protected action checks authorization, not just authentication.
- Sessions/tokens expire, rotate, and are invalidated on logout.
- No security decisions made on the client side alone.

## Data & privacy
- Collect the minimum personal data needed; document why each field is stored.
- Encrypt sensitive data in transit and at rest.
- Don't log PII or secrets. Define retention and deletion for personal data.

## Dependencies
- New packages: actively maintained, no known unpatched CVEs, compatible license.
- Pin versions; review transitive additions.

## Configuration
- Secure defaults (deny by default, least privilege).
- No debug endpoints, verbose errors, or stack traces exposed in production.

## On finding a secret
- Report its location only. Do not transmit, echo, or commit it. Recommend rotating it.
