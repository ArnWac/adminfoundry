# ADR-0003 — Bearer tokens instead of cookie sessions

**Status:** Accepted

## Context

The framework is **API-first**: it exposes a JSON contract for arbitrary
frontends, and ships a bundled admin UI as one consumer of that contract. Session
management could be:

1. **Server-side sessions + cookie** — classic web-app model. Needs server-side
   session storage, and cookies bring CSRF exposure (a cross-site request rides
   the ambient cookie) requiring a CSRF token layer.
2. **Stateless bearer JWTs** — the client sends `Authorization: Bearer <jwt>`;
   the server validates the signature and claims on each request. No server-side
   session store; CSRF is not applicable (no ambient credential is auto-attached
   by the browser to cross-site requests).

## Decision

Use **stateless bearer JWTs**. Two token types share the signing key but carry a
`type` claim and are validated differently (`access`, `impersonation`; plus
`refresh` and `mfa_challenge`). Revocation is layered on top of the stateless
model:

- **User-wide:** `User.token_version` — bump it and every prior token fails its
  `tkv` check (logout-everywhere); also implicit on deactivate.
- **Per-token:** a `RevokedToken` table keyed by `jti`, checked on every request
  (`is_token_revoked` in the auth dependency) — single-session logout.

Optional `iss`/`aud` pinning hardens multi-service deployments.

## Consequences

- **Positive:** no server-side session store; horizontal scale is trivial
  (stateless); clean fit for non-browser API clients; CSRF token machinery not
  needed.
- **Negative:** the bundled UI keeps the access token in `localStorage`, so an
  XSS in the UI can exfiltrate it — there is no `HttpOnly` protection. The
  mitigation is a strict **Content-Security-Policy** (`content_security_policy`),
  strongly recommended. As of G10 the bundled UI's inline scripts are
  **nonce-hardened**: putting `{nonce}` in `script-src` makes a strict
  `script-src 'self' 'nonce-{nonce}'` cover the UI without `'unsafe-inline'` (see
  [security.md](../security.md#known-limitations)). Revocation is not
  instantaneous for the user-wide path (a still-valid access token works until it
  expires or its `jti`/`token_version` is revoked).
- **Reconsider if:** a future requirement needs `HttpOnly` cookie storage — that
  would re-introduce a CSRF layer and warrants a superseding ADR.

See [security.md](../security.md#authentication) and
[auth-architecture.md](../auth-architecture.md).
