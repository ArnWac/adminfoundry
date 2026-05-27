---
name: project-adminfoundry-v1-refactor
description: Execution state of the adminfoundry v1 rebuild driven by adminfoundry_v1_next_phase_stabilize_core_then_mvp.md. Tracks the phase, what was done, and the exact resume point.
metadata:
  type: project
---

The user is executing a multi-phase rebuild of adminfoundry from `adminfoundry_v1_next_phase_stabilize_core_then_mvp.md`. They want ALL phases (0 through 9 plus MVP Security Foundation) done one after another, phase-by-phase with checkpoints (paused before each phase to confirm).

**Why:** The repo was mid-refactor — old monolithic adminfoundry architecture being torn out, new slim v1 core in place but not yet stabilized. The plan locks the next steps end-to-end.

**How to apply:** When resuming, re-read `adminfoundry_v1_next_phase_stabilize_core_then_mvp.md` then continue from the phase below. Confirm with the user before each phase starts.

## Decisions made at planning time

- examples/basic_multi/ → deleted entirely (was full of legacy refs).
- migrations/{shared,tenant}/versions/* → deleted; env.py files rewritten to use new architecture. Start migrations fresh later.
- ModelAdmin → strict MVP set: model, label/plural/description, list_display, search_fields, ordering, readonly_fields, protected_fields, actions, calculated_fields. Everything else dropped.
- All phases 0–9 in scope.

## Phase status (as of pause)

- **Phase 0 audit:** done. 107 baseline tests passing. Only legacy in active code was examples/basic_multi/ + old Alembic migrations.
- **Phase 0 cleanup:** done. Tests still green (107 passed).
  - Deleted: examples/basic_multi/, migrations/shared/versions/*, migrations/tenant/versions/*
  - Rewrote: migrations/shared/env.py, migrations/tenant/env.py (env-var driven, new bases)
  - Slimmed: adminfoundry/registry/admin.py (ModelAdmin), adminfoundry/registry/registry.py (metadata), adminfoundry/contract/service.py (ModelContractMeta + FieldMeta), adminfoundry/schemas/builder.py (dropped extra_create_fields, computed_fields→calculated_fields), adminfoundry/schemas/serialization/serializer.py (dropped inline_fields, computed_fields→calculated_fields), adminfoundry/builtins/admin.py (removed dead attrs)
  - Updated: tests/contract/test_service.py to match new contract shape.
- **MVP Security Foundation: done.** 231 tests green (+123 new). All of S1–S6 complete.
  - Created: adminfoundry/security/{__init__.py, validation.py, sanitize.py}
  - Validators: validate_resource_name/action/tenant_slug/schema_name/permission_key/limit_offset
  - Wired into: registry.register, crud router resource lookup, contract router resource lookup, tenant bootstrap (slug + permission_keys), tenancy/schema_strategy._validate_schema_name, crud/query.normalize_limit_offset, authz/permissions.permission_key
  - sanitize_payload: word-boundary key matching, scalar-only redaction (nested dicts/lists recursed)
  - Token wildcard logic in authz/permissions._matches_permission updated: `admin.*` now correctly grants any deeper key (was previously exact-depth match)
  - Tests added in tests/security/: test_validation.py (~40 cases), test_sanitize.py (10), test_auth_invariants.py (17 incl. rate limiter), test_crud_field_protection.py (16), test_legacy_guard.py (14 forbidden-pattern + package-tree)
  - Updated: tests/authz/test_permissions.py (two stale cases for old `admin.*` semantics), tests/tenancy/test_schema_names.py (hyphens in schema names now invalid; slug→schema translation handles it)
- **No commits yet this session.** Pre-session refactor + all my Phase-0 + MVP-Security changes are still unstaged.

## Phase 1 — done

259 tests green (+28 from Phase 1).

- Refactored adminfoundry/tenancy/bootstrap.py into composable, idempotent steps: create_tenant_record, assign_owner_membership, seed_default_tenant_roles, provision_tenant_schema, bootstrap_tenant. Seeding is DB-agnostic for unit tests; bootstrap_tenant Postgres path is no-op on SQLite.
- Owner role always receives admin.* (fallback). Admin gets catalog minus deny list (admin.audit.delete, admin.users.delete). Viewer gets catalog keys ending in .list. All assignments idempotent via existing-key diff.
- adminfoundry/cli/main.py rewritten: tenant create/list/bootstrap + improved doctor (config + DB check) + create-superadmin promotes-existing. tenant create flags: --name, --slug, --owner-email, --create-owner, --owner-password, --owner-full-name, --skip-schema.
- adminfoundry/tenancy/__init__.py exports the new helpers.
- Fixed latent bug: tenant_rbac.py had duplicate index definitions (Index(...) + index=True on same column). Created sqlite "index already exists" errors when TenantBase.metadata.create_all ran.
- adminfoundry/models/tenant.py had a wrong import path (validate_schema_name from .sanitize); fixed to .validation.
- New tests: tests/tenancy/test_bootstrap.py (13), tests/cli/test_cli.py (15).
- Note: tests/conftest.py engine fixture does NOT use schema_translate_map for SQLite — new tests use their own engines with the translate_map. If a future fixture wants to create global+tenant metadata on SQLite, copy the pattern from tests/tenancy/test_bootstrap.py.

## Phase 2 — done

273 tests green (+14 from Phase 2).

- Cleaned contract module: dropped unused `registry=` parameter from `build_model_contract` and from router code. CONTRACT_VERSION now re-imported.
- Added `tests/contract/test_router.py` (14 tests) covering: full + per-resource shape, app-registered admin, built-in tenant admins (tenant_roles / tenant_role_permissions / tenant_membership_roles), global model exclusion (users/tenants/tenant_memberships not in default contract), hidden field omission (globally protected + per-admin protected), invalid-resource-name → 404, path-traversal → 404, unauthenticated → 401, calculated field marked read_only+calculated, admin_actions defaults to [].
- Updated `tests/contract/test_service.py::test_contract_with_registry` (now `test_contract_works_after_registration`) to drop the registry= argument.

## Phase 3 — done

300 tests green (+27 from Phase 3).

- TenantAuthContext.has_permission() now delegates to authz.permissions.has_permission() (wildcard-aware). Previously did exact match only — was inconsistent with the CRUD router behavior.
- Added tests/crud/test_router_permissions.py (27 tests) covering: list/read/create/update/delete permission enforcement, pagination envelope shape, pagination bounds (limit capped at 500, negative offset clamps to 0), search filter, hidden-field omission in list/detail responses, hidden/readonly/unknown field rejection on create/update, 404 for unknown record + invalid resource name + path traversal, 422 for invalid primary-key coercion, is_system=True delete guard → 409, resource wildcard, global wildcard, cross-namespace wildcard rejection.
- Test pattern: build full app via create_admin(), override get_current_user + require_tenant_auth_context dependencies to inject a TenantAuthContext with a controlled permission_keys set. No tenant middleware needed.

## Phase 4 — done

316 tests green (+16 from Phase 4).

- Deleted entire adminfoundry/ui/templates/admin/ subdir (11 legacy templates: base/confirm_delete/create/detail/list/login/nav/password_reset_*/settings/update).
- Deleted adminfoundry/ui/static/admin/admin.i18n.js.
- Created adminfoundry/ui/templates/login.html (minimal: form + JS hook into /api/v1/auth/login, redirects to /admin/dashboard).
- Created adminfoundry/ui/templates/app.html (minimal SPA shell: data-view/data-resource/data-record-id attrs on body, single #app-root container, signout button, bootstraps ADMINFOUNDRY config from server).
- Rewrote adminfoundry/ui/static/admin/admin.css (minimal layout — login form + topbar only).
- Rewrote adminfoundry/ui/static/admin/admin.js as a minimal shell (login submit → fetch /api/v1/auth/login → store token; app pages → redirect to /login if no token; signout button clears token).
- Created adminfoundry/ui/__init__.py exposing router + STATIC_DIR + TEMPLATES_DIR.
- adminfoundry/core/installers.py: install_routes now mounts StaticFiles at <ui_path>/static BEFORE include_router so the catch-all /{resource} doesn't swallow static asset requests.
- tests/ui/test_router.py: 16 tests cover all 9 routes (200 + 302 root redirect), static.css/js content-types, unknown static path 404, only-minimal-templates guard (asserts only app.html + login.html exist), no-admin-subdirectory guard, no-legacy-static-assets guard, and the enable_builtin_ui=False switch returning 404.

## Phase 5 — done

333 tests green (+17 from Phase 5).

- tests/registry/test_calculated_fields.py covers the full ``calculated_fields`` contract end-to-end:
  - per-subclass default isolation (init_subclass guard)
  - contract.fields entries marked calculated=True + read_only=True
  - no DB column required
  - serializer emits values on detail AND list
  - exceptions inside the callable → null (no leak)
  - rejected on create + update via clean_write_payload (422)
  - HTTP integration: GET list/detail include values, POST/PATCH with calculated field → 422, PATCH update of underlying field updates the computed value (live recompute)
- No production code changes required — all wiring was already in place from Phase 0 (computed_fields → calculated_fields rename).

## Phase 6 — done

352 tests green (+19 from Phase 6).

- Slimmed adminfoundry/actions/__init__.py: kept only AdminAction (base) + BulkDeleteAction. Dropped DeactivateUsersAction, ActivateUsersAction, DisableTenantAction, EnableTenantAction (legacy, target tenant-local Users/Tenants which are root-only models). Dropped `async_execution` field — async actions are parked.
- AdminAction.to_dict() now returns just {name, label}. Slimmer contract.
- New adminfoundry/actions/router.py: POST /api/v1/admin/{resource}/_actions/{action} with body {"ids": [...]}. Validates resource + action name via security validators (→ 404), looks up admin (404), finds action by name (404), enforces admin.<resource>.<action> via TenantAuthContext.has_permission (403), coerces PKs, fetches records, calls action.execute(records, session, user). Wraps non-dict results as 500.
- adminfoundry/core/installers.py: actions router included BEFORE crud router so /{resource}/_actions/{action} matches first.
- tests/actions/test_router.py (19 tests): rename/delete/wildcard/missing-perm/cross-namespace/unknown-resource/unknown-action/invalid-action-name/invalid-resource-name/missing-body/wrong-ids-type/empty-ids-default/non-dict-result-500/contract-surface/AdminAction-base-NotImplementedError/to_dict-shape.

## Phase 7 — done

373 tests green (+21 from Phase 7).

- New module adminfoundry/audit/ with three public helpers:
  - `audit_payload(...)` builds an AuditLog with sanitized `changes` (no I/O)
  - `record_audit_in_session(session, ...)` adds the row inside a `session.begin_nested()` SAVEPOINT and swallows internal errors — preferred from request handlers since the audit row commits with the main txn (no separate writer connection)
  - `record_audit(db, ...)` opens an isolated session — used by login (where the failure paths raise an HTTPException that would otherwise roll back an in-session audit row) and by future CLI/lifecycle hooks
  - Plus canonical action-name constants: LOGIN_SUCCESS/FAILURE, CRUD_CREATE/UPDATE/DELETE, ADMIN_ACTION, IMPERSONATION_START/STOP
  - `request_audit_kwargs(request, status_code=...)` extracts method/path/status_code/ip_address
- All audit values pass through sanitize_payload (no raw passwords/tokens land in the audit changes column).
- Wired into auth.router (login success + 3 failure paths → record_audit, separate session), crud.router (create/update/delete → record_audit_in_session), actions.router (admin_action → record_audit_in_session). Route-level try/except wraps the audit helper as defense in depth so a buggy audit can never surface as 500.
- DatabaseManager now applies `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000` on every SQLite connection so independent writer sessions don't deadlock immediately on the "database is locked" error.
- tests/audit/test_service.py: 12 unit tests — record_audit basics, sanitization, actor capture, record_id stringification, no changes → null, isolated session, swallowed internal errors; audit_payload sanitize/stringify/none; record_audit_in_session commit with outer txn + swallowed errors.
- tests/audit/test_integration.py: 9 HTTP tests — login success/failure (3 reasons) write rows, CRUD create/update/delete write rows, admin action writes row, failed CRUD does NOT audit, audit-helper raising does not break response.

Notes / known limitations:
- In-session audit rows are rolled back if the main txn fails (acceptable: a failed CRUD op produces nothing to audit anyway).
- Login uses isolated session because the failure paths raise after audit; the read-only login session has no pending writes, so the second writer doesn't deadlock on SQLite.
- Retention cleanup, audit UI, metrics dashboard are explicitly parked.

## Phase 8 — done

388 tests green (+15 from Phase 8).

- Added root_api_prefix to CoreAdminConfig (default `/api/v1/root`, env `ADMINFOUNDRY_ROOT_API_PREFIX`) plus validate() + to_safe_dict() wiring + env override.
- New adminfoundry/root/ package: router.py aggregator + impersonation.py with POST /api/v1/root/impersonate.
- Endpoint requires `require_superadmin` (rejects impersonation tokens — proven in Phase 8 tests and reused in Phase 9 root routes).
- Request body: {target_user_id, tenant_id?, duration_minutes?}. Returns {access_token, token_type, expires_in (seconds), target_user_id, tenant_id}.
- Validates target exists + is active; validates tenant exists + is active if provided; rejects self-impersonation; clamps duration_minutes to [1, 480] via pydantic.
- Persists ImpersonationLog (superadmin_id, target_user_id, tenant_id, jti).
- Writes IMPERSONATION_START audit row inside the request session (savepoint-isolated, swallowed externally) with jti matching the log row for later revocation lookup.
- Fixed latent duplicate-index bug in adminfoundry/models/impersonation_log.py (Index(...) + index=True on superadmin_id/target_user_id/tenant_id) — same pattern as the tenant_rbac fix in Phase 1.
- adminfoundry/core/installers.py: root_router included after contract_router, before UI/actions/CRUD.
- tests/security/test_legacy_guard.py: added "root" to the allowed package guard.
- tests/root/test_impersonation.py (15 tests): unauth → 401, normal user → 403, impersonation token cannot re-impersonate, superadmin success, minted token is impersonation type with correct sub + impersonated_by, /auth/me reflects impersonated user with is_impersonating=true, require_superadmin rejects impersonation token even when target is a superadmin, ImpersonationLog row written with jti, audit row written with matching jti, self-impersonation → 400, unknown target → 404, inactive target → 409, duration out of bounds → 422, unknown tenant → 404.

## Phase 9 — done

407 tests green (+19 from Phase 9). All v1 MVP phases complete.

- adminfoundry/root/users.py: GET /api/v1/root/users + /users/{user_id}. Hand-written UserOut (id, email, full_name, is_active, is_superadmin) — hashed_password + token_version never reach the wire. Search filters email + full_name (ilike). Pagination via validate_limit_offset.
- adminfoundry/root/tenants.py: GET /api/v1/root/tenants + /tenants/{tenant_id}. Hand-written TenantOut (id, slug, name, schema_name, is_active). Search filters slug + name.
- adminfoundry/root/router.py: aggregates impersonation + users + tenants.
- tests/root/test_root_routes.py (19 tests): /users + /tenants — auth gates, superadmin success, search, pagination bounds, detail-by-uuid, 404 unknown, 422 invalid uuid, no hashed_password leak; isolation invariant (root models not registered as tenant CRUD admins).

## Final state — pre-v1 MVP complete

407 tests green. Forbidden legacy patterns: 0 in active code (per tests/security/test_legacy_guard.py).

## Production-Ready PRs done (per adminfoundry_v1_production_ready_core_claude_prompt.md)

576 tests green total (407 from MVP + 169 from PR-1..PR-10). 0 deprecation warnings. ruff + ruff format clean.

- **PR-1** Postgres infrastructure: pytest `postgres` marker, skip-if-unavailable conftest, real isolation tests in tests/postgres/ (10 tests).
- **PR-2** Alembic migrations: initial public + tenant schema versions, CLI commands `db upgrade-public/upgrade-tenant/upgrade-tenants/current/heads`.
- **PR-3** PermissionCatalog sync: adminfoundry.authz.catalog with generate_permission_keys + sync_permission_catalog, CLI `permissions sync/list/check`, bootstrap integration via optional registry= arg.
- **PR-4** Operational baseline: /healthz + /readyz, RequestIDMiddleware + SecurityHeadersMiddleware, structured JSON logging, CORS config + unsafe-config rejection, DB pool config.
- **PR-5** Consistent error envelope: {error: {code, message, fields, request_id, details}} across all error responses. AdminError class for custom envelopes.
- **PR-6** Packaging + CI: pyproject package-data fix (UI files were missing from wheel), py.typed marker, ruff config, GitHub Actions CI (lint+test+test-postgres+build matrix).
- **PR-7** Docs + Deployment: README + 5 docs/*.md rewrite, examples/basic_single fix (dropped attrs), Dockerfile, .env.example.
- **PR-8** CLI gaps + logout-all: POST /api/v1/auth/logout-all (bumps token_version), CLI `user list/create/disable/enable` + `tenant disable/enable`.
- **PR-9** Rate limiter Protocol: async RateLimiterBackend Protocol, async InMemoryLoginRateLimiter as default, no Redis hard-dep.
- **PR-10** Quality cleanup: replaced HTTP_422_UNPROCESSABLE_ENTITY with HTTP_422_UNPROCESSABLE_CONTENT (FastAPI 1.0), `environment` config field with production guards (rejects debug=True, SQLite, short secret_key in prod), `audit prune --days N` CLI, doctor enhanced (catalog, multi-tenant, CORS, registry via --app).

Production-ready gate is complete. The next round of work would draw from the parked-features list at the bottom of the production-ready prompt: Redis rate limiting backend impl, refresh tokens, single-token logout (RevokedToken), 2FA, password reset, dashboard widgets, extensions, import/export, jobs, workflows, S3, SCIM/SAML, OAuth, metrics, webhooks.

Future work menu (all parked per plan): Redis rate limiting, refresh tokens, 2FA, password reset, audit UI, dashboard widgets, import/export, jobs, workflows, SCIM/SAML, OAuth, metrics dashboard, webhooks.

## Block A/B/C/D refactor — DONE (2026-05)

Per `adminfoundry_admin_package_gap_analysis.md` the user asked to work
the four open architecture blocks. **1038 tests green** at the end of
the session (from a 576 baseline at session start, +462 new tests).

- **Block A (A1–A6):** Field Registry under `adminfoundry/fields/`
  (`FieldAdapter` Protocol, `FieldContract`, scalar adapters + FK
  adapter). Contract bumped to v2 with first-class `widget` /
  `required` / `help_text` / `validation` / `capabilities` /
  `relations` / `fieldsets` / `inlines` / `filters`.
  `AdminRuntime.fields: FieldRegistry`. `SchemaBuilder` +
  `contract/service.py` consult the registry instead of the inline
  `_TYPE_MAP`. `Fieldset` dataclass under `adminfoundry/admin/fieldset.py`.
  `RelationMeta` introspected from `mapper.relationships`.
- **Block B (B1–B4):** Lifecycle hooks on `ModelAdmin`
  (`before_validate` / `validate_create` / `validate_update` /
  `before_create` / `before_update` / `before_delete` / `after_*`).
  CRUD services + import_export call them when `ctx` is passed; legacy
  `ctx=None` callers still work. `AdminPolicy` class in
  `adminfoundry/admin/policy.py` with object-level gates
  (`can_view_model` / `can_create` / `can_view_object` /
  `can_update_object` / `can_delete_object`) plus per-field
  `field_permission(...)` returning a `FieldPermission` enum
  (`WRITE` / `READ` / `HIDDEN`). Serializer + clean_write_payload
  honour it. Actions intentionally not wired into hooks (signature
  changes in C3 instead).
- **Block C (C1–C3):** `InlineAdmin` in `adminfoundry/admin/inline.py`
  with full transactional parent+children write path
  (`process_inline_writes`, `split_parent_payload`). Wire format:
  `payload.inlines[<child_table>] = [{...}, {id: 5, ...}, {id: 6, _delete: true}]`.
  C2+ add-on: `fetch_inline_children` + `_augment_with_inlines`
  inject the child rows into POST / PATCH / GET responses (list
  endpoint deliberately omits inlines for N+1 protection). Typed
  actions: `AdminAction.run(objects, data, ctx)` + `input_schema` +
  `confirm` + `bulk` flags. Router prefers `run` when subclass
  overrides it, falls back to `execute` otherwise. Row-action endpoint
  `POST /{resource}/{record_id}/_actions/{action}` added beside the
  bulk endpoint.
- **Block D (D1–D4):** D1 — `filter_fields` on ModelAdmin →
  `?filter_<field>=value` parsed in `crud/query.py:parse_filter_query`,
  applied via `apply_filters`. D2 — `SavedFilter` global model +
  `/api/v1/admin/_saved_filters` CRUD router (per-user, per-tenant
  scoping, upsert semantics on the (user, resource, name) tuple).
  D3 — row-action endpoint (see Block C). D4 — export endpoint
  consults the same filter parser so "export current view" mirrors
  the on-screen filter set; audit row carries the filter dict.
  Column visibility is intentionally client-side (the SavedFilter
  payload field can carry it).

### Late additions outside the original four blocks

- **C2+ (inline-read):** `fetch_inline_children` + `_augment_with_inlines`
  so GET / POST / PATCH bring inline children back. List endpoint
  excluded.
- **§9 `user_mode` flag:** `CoreAdminConfig.user_mode = "builtin" | "external"`
  (env: `ADMINFOUNDRY_USER_MODE`). `external` mode requires an
  explicit `auth_provider` on `create_admin` — fails loudly instead
  of silently falling back to the builtin JWT stack.

### Wire-format compatibility

Contract bumped from `"1"` → `"2"`. All v1 wire fields stayed (no
removal); the new fields ship with safe defaults (empty list, None,
or "every capability allowed when no caller context"). Pre-A4 clients
that ignore unknown fields keep working.

### Status going into the next session

All Gap-Analysis P0+P1 items now closed (§4 InlineAdmin, §5 Field
Registry, §6 Contract API, §7 Hooks, §8 Policy, §9 user_mode, §10
Typed Actions, §11 Fieldsets, §12 List View). Roadmap's P2 / "later"
items remain explicitly parked: Tabs / Conditional Fields,
M2M-Inlines with assoc-table editing, validation hints in adapters,
extensions E2–E7 (workflows, webhooks, jobs, observability, dashboard,
storage), enterprise (2FA, SCIM/SAML, refresh tokens, ...).

## Key facts to remember

- Multi-tenant uses schema-per-tenant via `SET LOCAL search_path` on the shared session. No per-tenant engines.
- `request.app.state.adminfoundry` is the only runtime accessor (no globals).
- Permission keys: `admin.<resource>.<action>`, wildcards only at end (`admin.*`, `admin.<resource>.*`). NO middle wildcards.
- Tenant-local RBAC tables: TenantRole, TenantRolePermission, TenantMembershipRole (live INSIDE tenant schema, no tenant_id column).
- TenantAuthContext.has_permission() does EXACT match only — but the CRUD router uses authz.permissions.has_permission() which DOES wildcard match. Note this inconsistency; the plan likely wants context.has_permission() to use the wildcard-aware helper. Check during Phase 3.
- CLI is in adminfoundry/cli/main.py but lacks `tenant create`, `tenant list`, `tenant bootstrap` (only has migrate/upgrade). Add these in Phase 1.
- Contract was slim pre-Block-A — `FieldMeta` had {name, type, primary_key, read_only, hidden, nullable, calculated}. As of A4–C1+D1 the wire shape is much richer (see "Block A/B/C/D refactor" section above for the full diff). Contract version is now `"2"`.
- Field adapter registry: `AdminRuntime.fields: FieldRegistry`. Extensions can prepend custom adapters during their setup phase (the plumbing is in place, no extension uses it yet).
- Hook firing order CREATE: `can_create` → `before_validate` → schema clean → `validate_create` → `before_create` → INSERT → `after_create` → serialize → augment-with-inlines.
- Hook firing order UPDATE: fetch obj → `can_update_object` → field-policy apply to schema → `before_validate` → schema clean → `validate_update` → `before_update` → write → `after_update`.
- Hook firing order DELETE: fetch obj → `can_delete_object` → `before_delete` → `is_system` guard → DELETE → `after_delete`.

See [[feedback-adminfoundry-style]] for collaboration preferences.
