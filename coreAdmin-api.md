# coreAdmin-api — Prompt Suite

## Global contract for every phase

### Instruction priority
1. Security invariants
2. Current phase objective and acceptance criteria
3. Locked and stable constraints from earlier phases
4. Compatibility requirements
5. Reference notes
6. Build order

### Security invariants
- Never expose secrets, hashed secrets, token internals, database credentials, or protected internal fields in any response schema or serialized payload.
- Passwords, hashed passwords, PIN hashes, shared secrets, tenant salts, setup codes, QR bootstrap tokens, and equivalent protected fields must never appear in list, detail, create, or update response payloads.
- Read-only fields must be enforced at the API boundary, not only at UI or registry level.
- Superadmin-only routes must reject impersonation tokens unless a phase explicitly allows them.
- Audit failure must never change the functional response path.

### Compatibility contract
- Python 3.11+
- Async request and database paths by default
- SQLAlchemy 2.x style
- Pydantic v2
- UUID primary keys server-side
- UTC timestamps
- Absolute imports only
- Public collection endpoints return `PaginatedResponse[T]` unless the current phase explicitly exempts an endpoint

### Stability classes
- **Locked**: do not change unless the current phase explicitly allows it.
- **Stable**: minimal internal changes allowed only if required for correctness, compatibility, security, or tests.
- **Open**: free to add or refine within the phase scope.

### Conflict handling
If requirements conflict:
1. preserve security invariants
2. preserve external API behavior already established
3. satisfy current phase acceptance criteria
4. choose the smallest internal change
5. leave a brief code comment where a compromise was necessary

### Forbidden shortcuts
- Do not treat SQLite-only success as proof for PostgreSQL-critical behavior.
- Do not use `create_all()` as the only verification path once migrations become mandatory.
- Do not expose raw ORM objects via `__dict__`, implicit dumps, or unfiltered generic serialization.
- Do not silently fall back from tenant-scoped access to shared data access.
- Do not weaken protected-field filtering to satisfy generic CRUD generation.
- Do not skip regression tests for earlier phase behavior.
- Do not assume reference snippets are correct if framework constraints or tests prove otherwise.

### Test layers
- **fast**: no Docker required; lightweight isolated DB allowed; used for pure logic, serializers, builders, request validation, auth flow basics, router behavior, and protected-field filtering when PostgreSQL semantics are not essential.
- **integration**: real PostgreSQL required; run migrations; used for constraints, Alembic behavior, tenant schemas, schema scoping, transaction behavior, UUID/JSON/PostgreSQL-specific behavior.
- **e2e**: a few end-to-end flows through the real app stack; used only for high-value critical paths.

### Test rules by phase
- Phase 0: fast only
- Phase 1: fast required; integration optional
- Phase 2: fast required; integration recommended for persistence and constraints
- Phase 3: fast required; integration required
- Phase 4: fast required; integration required for compatibility with tenant and PostgreSQL behavior
- Phase 5: fast required; integration required; a few e2e flows required

### Migration test rule
From Phase 3 onward, PostgreSQL integration tests must apply Alembic migrations. Metadata-only setup is insufficient for tenant and migration verification.

### Output discipline
- Prefer concise code comments over prose.
- Prefer measurable acceptance criteria over qualitative claims.
- Reference snippets are illustrative, not authoritative.

---

# Phase 0 — Development foundation

## Objective
Create the project skeleton, tooling, configuration, migration layout, and local development baseline. No application logic.

## Locked
None.

## Stable
None.

## Open
Project structure, tooling files, migration scaffolding, dev workflow files.

## Deliverables
- `coreAdmin_api/` package root with empty `__init__.py`
- `tests/` package root with empty `__init__.py`
- shared and tenant Alembic directories with env files, templates, and empty versions directories
- `pyproject.toml`
- `alembic_shared.ini`
- `alembic_tenant.ini`
- `docker-compose.yml`
- `Makefile`
- `.env.example`
- `.gitignore`
- `README.md`

## Hard requirements
- Use Python 3.11+
- Configure FastAPI, SQLAlchemy async, Alembic, Pydantic settings, Typer, test dependencies
- Shared and tenant migration environments must exist from the beginning
- Local dev must support a PostgreSQL service through Docker Compose
- `.env.example` must contain all configuration keys required by later phases

## Acceptance criteria
- project structure matches the requested layout
- editable install works
- `pytest` runs successfully even if zero tests exist
- `make install` succeeds
- `docker-compose up` starts PostgreSQL cleanly
- both Alembic environments exist and are invokable
- no app logic files are created beyond basic placeholders

## Tests
- fast only
- verify importability and basic command success where practical

## Build order
1. folders and empty package files
2. `pyproject.toml`
3. Alembic ini files
4. migration env files and templates
5. Docker Compose and Makefile
6. `.env.example`
7. `.gitignore`
8. install and smoke-check commands

---

# Phase 1 — Core shared app foundation

## Objective
Implement shared settings, database session management, base models, user model, auth basics, health endpoint, error handling, pagination schema, and seed CLI.

## Locked
- Phase 0 migration env structure and tooling files

## Stable
- Phase 0 package layout

## Open
- shared app modules
- tests for auth and health

## Deliverables
- `settings.py`
- `database.py`
- `main.py`
- `cli.py`
- `models/base.py`
- `models/user.py`
- `schemas/common.py`
- `schemas/auth.py`
- `schemas/user.py`
- `routers/auth.py`
- `routers/health.py`
- `middleware/errors.py`
- `dependencies.py`
- tests for auth and health

## Hard requirements
- shared DB session dependency with rollback on exception
- JWT access and refresh tokens
- `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/me`
- `/health`
- structured validation and HTTP error responses
- CORS wired from settings
- pagination schema defined for future list endpoints
- CLI command to create first superadmin
- shared Alembic metadata must include shared models

## Acceptance criteria
- `UserPublic` excludes password and hash fields
- invalid credentials return 401
- inactive user cannot authenticate
- refresh accepts only refresh tokens
- `/me` returns authenticated user only
- `/health` reports degraded status if DB check fails
- validation errors return normalized JSON shape
- existing response payloads do not include secrets or hashes
- all Phase 1 tests pass

## Tests
- fast required
- integration optional
- cover success and failure cases for login, refresh, me, health, validation, and no-traceback error handling
- add at least one regression assertion that protected fields are absent from responses

## Build order
1. settings
2. base and user model
3. shared DB layer
4. shared migration metadata wiring
5. schemas
6. dependencies
7. health router
8. auth router
9. error middleware
10. app entrypoint
11. CLI
12. fast tests

---

# Phase 2 — Shared admin foundation: users, roles, logging

## Objective
Add user CRUD, simplified roles, role checks, superadmin checks, and structured request logging.

## Locked
- Phase 0 tooling and migration envs
- Phase 1 public auth endpoints and response contracts

## Stable
- `settings.py`
- `database.py`
- `models/base.py`
- `models/user.py`
- `routers/health.py`
- `tests/conftest.py` existing fixtures

## Open
- role model and schemas
- user and role routers
- logging middleware
- new tests

## Deliverables
- `models/role.py`
- `schemas/role.py`
- extend `schemas/user.py` with create and update schemas
- extend `dependencies.py` with `require_role` and `require_superadmin`
- `routers/users.py`
- `routers/roles.py`
- `middleware/logging.py`
- tests for users and roles

## Hard requirements
- roles are names only, no permission matrix
- superadmin bypasses role checks
- user list and role list endpoints paginate
- duplicate emails and duplicate role assignments are rejected cleanly
- logging middleware must emit request id and set `X-Request-ID`
- logging must not change successful endpoint behavior

## Acceptance criteria
- superadmin can create, read, update, and soft-delete users
- non-superadmin cannot access superadmin-only routes
- duplicate email creation returns conflict
- role can be created, assigned, removed, and listed
- `require_role("manager")` returns 403 without role and succeeds with role
- structured logs are emitted for requests
- `X-Request-ID` is present on responses
- all Phase 1 tests still pass unchanged
- all new Phase 2 tests pass

## Tests
- fast required
- integration recommended for DB constraints and duplicate handling
- add regression tests for auth endpoints after middleware wiring
- assert soft-delete means `is_active=False`, not physical deletion

## Build order
1. role model
2. migration and upgrade
3. role schema and user schema extension
4. dependencies extension
5. users router
6. roles router
7. logging middleware
8. app wiring
9. fast tests
10. optional integration tests

---

# Phase 3 — Multi-tenancy behind feature flag

## Objective
Add multi-tenancy behind `MULTI_TENANT` while preserving zero regressions when the flag is false.

## Locked
- all Phase 0 tooling
- Phase 1 auth endpoint contracts
- Phase 2 router contracts unless explicitly extended

## Stable
- `settings.py` except explicitly allowed additions
- `database.py`
- `tests/conftest.py` existing fixtures

## Open
- tenant model, schema, router, middleware
- database tenant support
- CLI tenant migration commands
- tenant tests

## Deliverables
- `models/tenant.py`
- `schemas/tenant.py`
- `routers/tenants.py`
- `middleware/tenant.py`
- extend `database.py` with tenant engine cache and tenant DB dependency
- extend `dependencies.py` only as needed for tenant DB use
- extend `cli.py` with tenant migration commands
- tests for tenant CRUD, resolution, and isolation

## Hard requirements
- when `MULTI_TENANT=false`, shared mode must behave exactly as before
- when `MULTI_TENANT=true`, tenant-scoped access must require resolved tenant context
- tenant resolution must support explicit header strategy and host-based strategy if enabled by the prompt
- tenant-scoped DB access must never silently fall back to shared data
- PostgreSQL schema scoping must be implemented for shared-database tenants
- tenant routes must remain superadmin-only unless explicitly stated otherwise
- user model may add tenant foreign key in this phase only

## Acceptance criteria
- tenant create, read, update, disable, and migrate flows work
- invalid slug returns validation failure
- duplicate slug returns conflict
- disabled tenant is rejected by tenant middleware
- requests missing tenant context in multi-tenant mode fail explicitly
- tenant A data is not visible under tenant B context
- single-tenant tests from earlier phases still pass unchanged when flag is false
- integration tests run against real PostgreSQL with Alembic migrations

## Tests
- fast required for resolution logic, middleware branching, and schema validation
- integration required for migrations, schema creation, schema scoping, tenant isolation, transaction behavior
- e2e not required yet
- add regression tests proving single-tenant compatibility remains intact

## Build order
1. tenant model
2. user tenant FK change
3. migration and upgrade
4. tenant schema
5. database tenant support
6. tenant middleware
7. tenant router
8. CLI tenant migration commands
9. app wiring
10. fast tests
11. PostgreSQL integration tests with migrations

---

# Phase 4 — Registry-driven admin CRUD

## Objective
Add the model registry, schema builder, filter builder, serializer, and dynamic admin CRUD routes.

## Locked
- Phase 0 to 3 public behaviors
- tenant middleware behavior
- shared and tenant DB semantics

## Stable
- existing routers, models, middleware, and tests
- admin integration points may extend but must not weaken prior guarantees

## Open
- admin package
- registry schemas
- example integration
- new tests

## Deliverables
- `admin/model_admin.py`
- `admin/registry.py`
- `admin/schema_builder.py`
- `admin/filter_builder.py`
- `admin/serializer.py`
- `admin/router.py`
- registry-related schema module if needed
- package exports for `admin_site`, `ModelAdmin`, `create_coreadmin`
- example registration files
- tests for schema builder, registry, admin CRUD

## Hard requirements
- build and test `schema_builder.py` before wiring dynamic router behavior
- schema generation must filter protected fields globally and per-admin config
- generated create schemas must exclude auto and read-only fields
- generated update schemas must make fields optional
- dynamic CRUD must use filtered schemas, not raw ORM dumps
- registry metadata must not expose protected fields as editable fields
- tenant-scoped admin models must honor tenant context in multi-tenant mode
- readonly field mutation attempts must fail explicitly

## Acceptance criteria
- schema builder tests cover multiple distinct model configurations
- protected fields are absent from list, detail, create, and update schemas
- readonly fields produce 422 on attempted mutation
- dynamic list endpoints paginate and respect filtering, search, and ordering
- dynamic detail endpoints do not leak protected fields
- tenant-scoped models return only rows for the active tenant in multi-tenant mode
- registry output reflects list display, filters, ordering, readonly fields, and actions without exposing protected internals
- all Phase 1 to 3 tests still pass unchanged
- integration tests confirm compatibility with PostgreSQL and tenant scoping

## Tests
- fast required for schema builder, filter builder, serializer, registry behavior
- integration required for admin CRUD compatibility with PostgreSQL and tenant scoping
- add explicit regression tests that registry-driven CRUD does not bypass security rules from earlier phases

## Build order
1. model admin and registry
2. schema builder
3. schema builder tests only; must pass before continuing
4. filter builder
5. serializer
6. registry schema if needed
7. admin router
8. package exports and app integration
9. example registration files
10. fast tests
11. integration tests

---

# Phase 5 — Audit, impersonation, break-glass, logout

## Objective
Complete V1 with audit logging, impersonation, break-glass editing, token blacklist logout, and revocation flows.

## Locked
- Phase 0 to 4 public contracts and security invariants
- admin schema builder, registry, and router public behavior unless a narrow extension is required

## Stable
- existing middleware and router structure
- `routers/auth.py` may only be extended for logout and explicit token restrictions required by this phase

## Open
- audit and impersonation models
- token blacklist module
- audit and break-glass routers and middleware
- tenant router extensions for impersonation and revocation
- related schemas and tests

## Deliverables
- `models/audit_log.py`
- `models/impersonation_log.py`
- `token_blacklist.py`
- extend `dependencies.py` with blacklist and impersonation state
- extend `routers/auth.py` with logout and refresh restrictions
- extend tenant router with impersonation and revoke flows
- `routers/audit.py`
- `routers/break_glass.py`
- `middleware/audit.py`
- related schemas
- tests for audit, impersonation, break-glass, logout

## Hard requirements
- logout must revoke the current access token by JTI
- refresh must reject non-renewable tokens
- impersonation tokens must be non-renewable and rejected by superadmin-only routes unless explicitly allowed
- audit middleware must never break the main request flow if audit write fails
- if diff capture is not robust, a minimal audit record is still mandatory
- break-glass must require a meaningful reason and must write both master and tenant audit records where applicable
- break-glass must reject protected and read-only fields
- impersonation revocation must blacklist the impersonation token

## Acceptance criteria
- logout invalidates the current access token
- refresh still works with a valid refresh token after logout unless refresh blacklisting is explicitly implemented
- impersonation token cannot be refreshed
- impersonation token is rejected by direct superadmin-only routes
- audit log records method, path, status, user, tenant, action, and object identifier whenever derivable
- successful break-glass returns evidence of dual audit writes
- short or missing break-glass reason returns validation failure
- protected or readonly break-glass edits are rejected
- all earlier phase tests still pass unchanged
- integration tests run against PostgreSQL with migrations
- a few e2e flows verify critical V1 behavior

## Required e2e flows
1. login -> logout -> same access token rejected
2. tenant creation -> tenant migration -> impersonation -> scoped action -> revoke -> scoped token rejected
3. break-glass edit -> dual audit presence verified

## Tests
- fast required for blacklist logic, token restrictions, and request validation
- integration required for audit persistence, impersonation log persistence, break-glass dual writes, and PostgreSQL-backed flows
- e2e required for the critical flows listed above

## Build order
1. audit and impersonation models
2. migration and upgrade
3. token blacklist
4. dependency extensions
5. auth router extension
6. audit router
7. tenant router impersonation extensions
8. break-glass router
9. audit middleware and app wiring
10. related schemas
11. fast tests
12. integration tests
13. e2e tests

---

# Phase 6 — Stable admin contract and capability model

## Objective
Stabilize a renderer-independent admin contract that exposes resource metadata, field metadata, permissions, capabilities, and tenant context explicitly for any UI client.

## Locked
- Phase 0–5 public API behavior
- security invariants from earlier phases
- auth, tenant, audit, impersonation, break-glass, and protected-field filtering semantics
- existing dynamic CRUD endpoint behavior unless explicitly extended

## Stable
- `admin/model_admin.py`
- `admin/registry.py`
- `admin/router.py`
- existing registry output shape may be extended but must not silently remove previously exposed safe metadata
- existing schemas and routers may be extended minimally for UI-contract support

## Open
- admin contract schemas
- capability and policy metadata
- admin context endpoints
- navigation metadata
- field widget hints and relation metadata
- tests for contract stability and filtering

## Deliverables
- extend `admin/model_admin.py`
- extend `admin/registry.py`
- extend `admin/router.py`
- new `schemas/admin_contract.py`
- new `schemas/navigation.py`
- new `schemas/capabilities.py`
- new `admin/contract.py`
- new `admin/navigation.py`
- new `admin/capabilities.py`
- new `/admin/context` endpoint
- new `/admin/navigation` endpoint
- new `/admin/capabilities` endpoint
- new `/admin/registry/{model}` endpoint or equivalent detailed metadata endpoint
- tests for contract, capabilities, metadata filtering, relation metadata, and admin context

## Hard requirements
- admin metadata must be explicit and renderer-independent
- built-in web UI and future external clients must consume the same admin contract
- protected, internal, and server-only fields must never appear in UI metadata
- clients must never require ORM inspection, `__dict__`, model reflection, or hidden conventions
- model metadata must distinguish list, detail, create, update, filter, and action presentation
- tenant-scoped models must be clearly marked in metadata
- capability metadata must expose allowed operations for the current user and tenant context in UI-safe form
- field metadata must expose readonly, required, nullable, default-present, sortable, filterable, searchable, and relation flags where applicable
- relation fields must expose enough metadata for generic selection and display without leaking backend internals
- action metadata must include label, danger state, confirmation requirement, bulk/single applicability, and permission gating
- admin context must expose current user, tenant context, impersonation state, and visible navigation/resources in a UI-safe format
- contract changes that affect clients must be snapshot-testable
- no model-specific UI logic may be required to render baseline generic list, detail, and form views

## Acceptance criteria
- `/admin/context` returns authenticated admin context without exposing secrets, token internals, or protected fields
- `/admin/navigation` returns visible navigation structure for the current user and tenant context
- `/admin/capabilities` returns UI-safe capability metadata for the current user and active context
- `/admin/registry` and detailed model metadata endpoints expose labels, field groups, filters, ordering, actions, relation metadata, and tenant scope flags
- protected fields are absent from CRUD schemas and from all admin contract responses
- metadata is sufficient to render generic list, detail, create, update, filter, and action screens without ORM inspection
- action metadata includes confirmation and danger metadata where applicable
- capability metadata correctly differs for superadmin, privileged non-superadmin, impersonated user, and denied user scenarios
- all Phase 0–5 tests still pass unchanged
- all new Phase 6 tests pass

## Tests
- fast required
- integration required
- e2e not required
- fast tests must cover contract generation, protected-field filtering, capability serialization, relation metadata, action metadata, and admin context shape
- integration tests must verify contract correctness under PostgreSQL and tenant-scoped conditions
- regression tests must prove that existing CRUD, auth, tenant, and audit behavior remains unchanged
- add contract snapshot tests for at least two representative models with different field and permission characteristics

## Build order
1. extend `ModelAdmin` metadata surface
2. add contract, capability, and navigation schemas
3. add admin context, navigation, and capability endpoints
4. extend registry and model metadata endpoints
5. add fast tests for contract and filtering
6. add integration tests for tenant and PostgreSQL compatibility
7. add contract snapshot tests

---

# Phase 7 — Lightweight built-in admin UI

## Objective
Provide an optional lightweight built-in web admin UI that covers the core operational flows and uses the Phase 6 admin contract as its single source of truth.

## Locked
- Phase 0–6 public API behavior
- security invariants
- protected-field filtering
- auth, tenant, impersonation, audit, and break-glass backend semantics
- Phase 6 admin contract endpoints as the authoritative UI interface

## Stable
- `admin/router.py`
- `admin/registry.py`
- `admin/contract.py`
- existing CRUD endpoints
- auth flows may be extended minimally only if required for UI bootstrap

## Open
- built-in admin UI router
- templates and static assets
- lightweight UI shell
- metadata-driven list/detail/form rendering
- UI configuration and mounting
- UI support matrix and fallback behavior
- UI smoke tests

## Deliverables
- new `routers/admin_ui.py`
- new `templates/admin/` directory
- new `static/admin/` directory
- optional `admin/ui_renderer.py`
- optional `admin/ui_helpers.py`
- app integration to mount the built-in UI
- optional UI settings such as `ENABLE_BUILTIN_ADMIN_UI` and mount path
- generic admin pages for:
  - login shell
  - navigation
  - list
  - detail
  - create
  - update
- new lightweight support-matrix metadata or equivalent renderer capability map
- tests for built-in UI rendering and basic flows

## Hard requirements
- built-in admin UI must be optional and package-provided
- built-in UI must consume the Phase 6 contract rather than duplicating backend model logic
- the built-in UI is intentionally lightweight and does not need full feature parity with future enterprise clients
- built-in UI must support only baseline generic admin flows in this phase
- unsupported metadata-driven features must degrade safely with explicit non-breaking fallback UI
- built-in UI must expose an explicit renderer support matrix so unsupported features are discoverable instead of silently ignored
- disabling built-in UI must not affect API behavior
- built-in UI must not expose secrets, protected fields, raw ORM internals, or hidden server-side metadata
- built-in UI must respect tenant context, impersonation visibility, readonly fields, protected fields, filtering, search, ordering, and pagination where supported in the baseline renderer
- delete and dangerous actions may be deferred to later phases if metadata-driven confirmation UX is not yet implemented
- built-in UI must remain accessible for baseline keyboard navigation and basic labeling
- built-in UI text and labels must be structured so later localization is possible without backend contract rewrites

## Acceptance criteria
- enabling the built-in UI exposes a working admin UI route
- admin login shell loads successfully
- registered models appear in built-in navigation according to user visibility rules
- generic list pages render from contract metadata
- detail pages render without exposing protected fields
- create and update forms render from metadata and enforce readonly and protected rules
- basic search, filter, ordering, and pagination work for supported models
- tenant context is visible and respected in tenant-scoped views
- unsupported advanced features render a safe fallback state rather than failing hard
- a renderer support matrix or equivalent capability indicator is available for the built-in UI
- disabling built-in UI leaves all existing API tests green
- all Phase 0–6 tests still pass unchanged
- all new Phase 7 tests pass

## Tests
- fast required
- integration required
- e2e required
- fast tests must cover route mounting, template helpers, support-matrix exposure, and lightweight rendering behavior
- integration tests must verify built-in UI behavior against PostgreSQL-backed admin flows and tenant context
- e2e tests must cover login, model navigation, generic list/detail/create/update flow, and basic filter/search behavior
- regression tests must prove API-only mode remains unchanged when built-in UI is disabled

## Build order
1. add built-in admin UI router
2. add templates and static assets
3. wire UI mount and configuration
4. render generic navigation, list, detail, create, and update views from contract metadata
5. add fallback handling for unsupported metadata hints and support-matrix exposure
6. add fast tests
7. add integration tests
8. add e2e smoke flows

---

# Phase 8 — Built-in UI completeness for core admin operations

## Objective
Expand the lightweight built-in admin UI to cover the most important operational features without trying to become the final enterprise-grade client.

## Locked
- Phase 0–7 public contracts
- security invariants
- built-in UI optionality
- Phase 6 contract as the primary renderer interface
- tenant and audit semantics

## Stable
- built-in UI shell and routing
- registry and metadata endpoints
- baseline generic CRUD behavior
- existing `ModelAdmin` metadata may be extended but not weakened

## Open
- delete and dangerous action UX
- break-glass UX
- audit visibility in UI-safe form
- richer validation and error presentation
- UI confirmation flows
- improved metadata fallback rendering
- personal UI preferences
- tests for operator-critical flows

## Deliverables
- extend built-in UI templates and helpers
- extend UI rendering for delete and action confirmation flows
- extend built-in UI to surface audit-related and impersonation-related safe context indicators
- extend UI to handle break-glass initiation where allowed
- new personal UI preference persistence or equivalent state layer for supported preferences
- tests for confirmation flows, validation handling, operator-critical pages, and preference persistence

## Hard requirements
- built-in UI must remain metadata-driven and renderer-independent at the backend contract layer
- dangerous actions must require explicit confirmation UX where metadata marks them as dangerous or confirm-required
- built-in UI must clearly show impersonation state and tenant context in UI-safe form
- break-glass initiation must require reason capture and must not bypass readonly or protected-field rules
- validation and authorization failures must render clearly without leaking backend internals
- built-in UI still does not need to implement every future feature from later phases
- unsupported advanced workflows must still degrade safely
- supported personal UI preferences may include visible columns, sorting, density, navigation favorites, and similar non-security preferences
- preference persistence must never override server-enforced permissions, field visibility, or protected-field filtering

## Acceptance criteria
- delete and supported dangerous actions require explicit confirmation in the built-in UI
- impersonation state is visible in UI-safe form where applicable
- break-glass flows can be initiated only where metadata and permissions allow
- validation failures render useful field-level or operation-level feedback
- audit-related safe indicators are visible where relevant
- supported personal UI preferences can be saved and restored for the current user
- all Phase 0–7 tests still pass unchanged
- all new Phase 8 tests pass

## Tests
- fast required
- integration required
- e2e required
- fast tests must cover confirmation rendering, error mapping, break-glass form handling, and preference serialization
- integration tests must verify dangerous action execution, break-glass initiation, preference persistence, and tenant-safe UI behavior under PostgreSQL
- e2e tests must cover delete confirmation, dangerous action confirmation, impersonation indicator visibility, break-glass reason submission, and preference roundtrip for at least one supported preference
- regression tests must prove baseline Phase 7 CRUD flows still work

## Build order
1. extend UI action and delete rendering
2. add confirmation flows
3. surface impersonation and tenant indicators
4. add break-glass initiation UX
5. add personal UI preference persistence for a small supported set
6. improve validation and error rendering
7. add fast tests
8. add integration tests
9. add e2e tests

---

# Phase 9 — External client contract stabilization

## Objective
Version and stabilize the admin contract so a separate external client such as Flutter can fully consume it without built-in-UI assumptions.

## Locked
- Phase 0–8 security invariants and API semantics
- built-in UI behavior as a valid reference implementation
- admin contract endpoints as the source of truth for renderer clients
- tenant, audit, impersonation, break-glass, and protected-field semantics

## Stable
- metadata endpoint families
- built-in UI integration
- `ModelAdmin` metadata fields
- auth and admin context endpoints
- capability and navigation structures may be extended minimally for external-client readiness

## Open
- contract versioning
- optional client configuration endpoint
- external-renderer metadata refinements
- compatibility policy and documentation
- relation lookup contract
- tests for contract stability and multi-client compatibility

## Deliverables
- explicit contract versioning for admin metadata endpoints
- optional `/admin/client-config` endpoint
- extend `/admin/capabilities` if needed for renderer/client feature flags
- extend contract schemas for external renderer hints
- explicit compatibility documentation for lists, detail views, forms, filters, actions, audit indicators, tenant context, dangerous-flow confirmations, and relation rendering
- explicit deprecation and compatibility policy for client-facing contract evolution
- relation lookup metadata and endpoints for generic async selection flows
- tests for contract stability, relation lookup behavior, and external-client compatibility
- optional example integration notes for Flutter

## Hard requirements
- built-in UI and external clients must use the same core admin contract
- external clients must not require ORM inspection, server internals, undocumented conventions, or built-in-UI-specific assumptions
- contract changes affecting clients must be versioned or compatibility-scoped
- the project must define what constitutes a breaking change versus an additive change for client-facing metadata
- metadata must be explicit enough for external rendering of generic list, detail, form, filter, action, context, and relation-selection flows
- relation fields must expose enough metadata for generic label resolution, async lookup, pagination, and tenant-safe option retrieval
- disabling built-in UI must not affect external-client support
- protected-field, tenant-isolation, and policy-related guarantees already established must remain unchanged
- contract snapshot tests must be usable as a release gate for representative models and contexts

## Acceptance criteria
- admin contract is explicitly versioned or compatibility-scoped for client consumption
- `/admin/context`, `/admin/navigation`, `/admin/capabilities`, registry/model metadata, relation lookup endpoints, and optional client-config endpoints are sufficient for an external client to render generic admin flows
- built-in UI and external-client contract expose consistent labels, field flags, capability metadata, action metadata, and tenant-scope information
- no protected fields appear in any external-client-facing metadata or capability response
- relation lookups function for at least one representative searchable relation and one paginated relation
- contract deprecation rules are documented and testable
- built-in UI can be disabled without breaking external-client metadata flows
- all Phase 0–8 tests still pass unchanged
- all new Phase 9 tests pass

## Tests
- fast required
- integration required
- e2e recommended
- fast tests must cover contract schemas, version negotiation or version selection behavior, deprecation metadata, relation metadata, and client-config/capability metadata
- integration tests must verify contract correctness under PostgreSQL and tenant-scoped scenarios, including relation lookup endpoints
- e2e tests should cover one built-in-UI flow and one external-client-style metadata-driven flow against the same backend
- regression tests must prove built-in UI and API-only modes remain functional
- contract snapshot tests must cover at least two representative models under at least three contexts such as superadmin, scoped user, and tenant-scoped user

## Build order
1. stabilize and version the admin contract
2. define and document deprecation and compatibility rules
3. add client-config and compatibility metadata if needed
4. add relation lookup metadata and endpoints
5. extend schemas for external rendering hints
6. write compatibility documentation and example Flutter consumption notes
7. add fast tests and snapshot gates
8. add integration tests
9. add optional e2e compatibility tests

---

# Phase 10 — Fine-grained authorization and policy engine

## Objective
Add explicit fine-grained authorization so resources, fields, actions, and records can be governed beyond simple role checks.

## Locked
- Phase 0–9 public contracts and security invariants
- protected-field filtering rules
- tenant isolation semantics
- auth token restrictions, impersonation restrictions, and break-glass guarantees

## Stable
- existing role model and role checks
- admin contract endpoints may be extended but must not remove existing safe metadata
- dynamic CRUD router structure
- built-in UI and external-client integration points

## Open
- policy engine
- capability evaluation layer
- field-level visibility and editability rules
- record-level access constraints
- policy metadata exposure to clients
- tests for policy enforcement

## Deliverables
- new `authz/policy_engine.py`
- new `authz/rules.py`
- new `schemas/policy.py`
- extend `dependencies.py` with policy evaluation helpers
- extend `admin/capabilities.py`
- extend `admin/contract.py`
- optional `models/policy_assignment.py` if persistence is needed
- tests for policy evaluation, field visibility, action permissions, and row-level restrictions

## Hard requirements
- policy enforcement must support more than route-level allow or deny
- field visibility and field editability must be separately representable and enforceable
- record-level restrictions must be enforceable server-side and must not rely on UI hiding
- capability metadata must reflect effective permissions for the current user and context in UI-safe form
- superadmin bypass must remain explicit and narrowly controlled
- impersonation tokens must not gain access beyond the impersonated identity and phase-specific restrictions
- policy failures must return explicit authorization errors without leaking hidden resource details beyond established API behavior
- break-glass must remain separately auditable and must not silently bypass protected-field or readonly protections unless a later phase explicitly allows it
- field and action permissions must remain consistent between API enforcement and admin contract exposure
- tenant-scoped access must not be weakened by policy abstractions

## Acceptance criteria
- a user can be allowed to view but not edit a field on the same resource
- a user can be allowed to edit some records but not others for the same model
- denied actions are absent or disabled in capability metadata and are rejected server-side if attempted directly
- record-level restrictions are enforced in list, detail, update, delete, and action flows
- policy evaluation correctly differentiates superadmin, role-based user, policy-granted user, impersonated user, and denied user scenarios
- protected fields remain absent regardless of policy grants
- all Phase 0–9 tests still pass unchanged
- all new Phase 10 tests pass

## Tests
- fast required
- integration required
- e2e required
- fast tests must cover policy resolution, field visibility and editability, action gating, and capability serialization
- integration tests must verify record-level restrictions, policy-backed list filtering, and tenant-safe enforcement under PostgreSQL
- e2e tests must cover visible-but-readonly field scenarios, denied bulk action scenarios, and policy-scoped record access
- regression tests must prove that prior role-based and superadmin flows still work

## Build order
1. add policy engine and evaluation helpers
2. extend capabilities and contract metadata
3. wire policy checks into CRUD and action paths
4. add fast tests for policy logic
5. add integration tests for record-level enforcement
6. add e2e tests for UI and direct API authorization flows

---

# Phase 11 — Jobs, import/export, and bulk operation safety

## Objective
Support realistic admin workflows through asynchronous jobs, safe bulk operations, and production-grade import/export flows.

## Locked
- Phase 0–10 public contracts and security invariants
- audit semantics and request logging behavior
- policy engine semantics and tenant isolation

## Stable
- action execution model
- built-in UI structure
- external-client contract
- admin contract and capability endpoints
- CRUD routes may be extended but not broken

## Open
- job model and runner integration
- async action execution
- import/export framework
- bulk operation safeguards
- result artifact handling
- idempotency and retry semantics
- tests for jobs and data movement flows

## Deliverables
- new `models/job.py`
- new `schemas/job.py`
- new `services/jobs.py`
- new `services/import_export.py`
- new `routers/jobs.py`
- extend action metadata and execution flow for async operation support
- import endpoints and export endpoints
- optional artifact storage abstraction
- idempotency key support or equivalent duplicate-execution protection for supported actions and jobs
- tests for jobs, import/export, retries, and bulk safeguards

## Hard requirements
- long-running admin operations must not require synchronous request completion
- actions must be able to declare synchronous or asynchronous execution mode
- jobs must expose status, progress, initiator, timestamps, tenant context, audit linkage, and result or failure summary in UI-safe form
- imports must support dry-run validation before commit
- imports must support row-level error reporting without leaking protected fields
- exports must honor effective permissions, field visibility rules, tenant scope, and protected-field filtering
- bulk operations must support explicit confirmation metadata and safe execution semantics
- destructive or high-impact bulk actions must support preview or impact summary before execution
- job execution failures must be visible without breaking unrelated request paths
- retries and repeated submissions must not create unsafe duplicate execution for operations declared idempotent or protected by idempotency keys
- audit records must link initiated jobs and resulting state-changing operations where derivable
- file or artifact outputs generated by import or export flows must remain permission-scoped and tenant-safe

## Acceptance criteria
- a supported bulk action can run asynchronously and expose job status transitions
- import dry-run returns validation results without mutating data
- confirmed import persists only allowed fields and rejects protected or readonly fields
- export output excludes hidden and protected fields for the effective user context
- high-impact bulk actions expose preview or confirmation metadata and reject execution without required confirmation
- a repeated supported request using the same idempotency key does not create duplicate execution
- job status, result summary, and failure summary are visible through API and built-in UI where supported
- all Phase 0–10 tests still pass unchanged
- all new Phase 11 tests pass

## Tests
- fast required
- integration required
- e2e required
- fast tests must cover job state transitions, import validation, export field filtering, idempotency handling, and bulk confirmation logic
- integration tests must verify persisted jobs, import commit behavior, export scope correctness, tenant-safe bulk execution, and idempotent retry behavior under PostgreSQL
- e2e tests must cover async bulk action initiation, job progress visibility, import dry-run plus commit, export initiation, and at least one duplicate-submission protection scenario
- regression tests must prove existing synchronous actions still work where unchanged

## Build order
1. add job model and schemas
2. add job service and async action support
3. add import/export service and endpoints
4. extend action metadata for preview, async execution, and idempotency handling
5. add built-in UI job views and import/export flows where appropriate
6. add fast tests
7. add integration tests
8. add e2e tests

---

# Phase 12 — Security hardening, sessions, and operational observability

## Objective
Make the admin operationally safe in production with stronger session controls, step-up security, rate limits, metrics, and alert-ready observability.

## Locked
- Phase 0–11 public contracts and security invariants
- auth, tenant, audit, impersonation, break-glass, and policy enforcement semantics
- protected-field filtering and export restrictions

## Stable
- auth router structure
- built-in UI routing
- external-client contract
- admin contract endpoints may be extended but must not break prior consumers
- job and action semantics

## Open
- MFA and step-up controls
- session or device management
- rate limiting and brute-force protection
- admin metrics and observability hooks
- secure-header configuration
- tests for hardening and telemetry behavior

## Deliverables
- extend `routers/auth.py`
- new `schemas/session.py`
- new `services/session_security.py`
- new `middleware/security_headers.py`
- new `middleware/rate_limit.py` or equivalent integration point
- new `observability/admin_metrics.py`
- optional session listing and revocation endpoints
- optional step-up auth endpoints or challenge flow
- tests for session controls, hardening, and observability

## Hard requirements
- critical admin actions must be able to require recent authentication or equivalent step-up proof
- built-in UI security model must explicitly handle CSRF, cookie or session strategy, or token transport strategy without ambiguity
- rate limiting or brute-force mitigation must protect login and other abuse-prone admin endpoints
- session handling must support explicit revocation beyond single-token logout where applicable
- admin responses must include safe security headers appropriate for the built-in UI delivery model
- metrics must exist for admin request counts, failures, latencies, action outcomes, job outcomes, audit-write failures, and contract-version usage where measurable
- telemetry should distinguish built-in UI and external clients where safely derivable
- telemetry must not expose secrets, token internals, or protected field content
- security hardening must not weaken impersonation restrictions, superadmin protections, or policy enforcement
- operational failures in metrics or telemetry must not change primary endpoint success semantics

## Acceptance criteria
- at least one critical action path can require recent-auth or equivalent step-up enforcement
- login abuse protection rejects repeated invalid attempts according to configured policy
- active admin sessions can be listed and selectively revoked where the session model supports it
- built-in UI responses include configured security headers
- metrics capture admin request, action, job, and client-contract usage counters without changing functional behavior
- audit write failure metrics are emitted when audit persistence fails in controlled tests
- all Phase 0–11 tests still pass unchanged
- all new Phase 12 tests pass

## Tests
- fast required
- integration required
- e2e required
- fast tests must cover rate-limit logic, session security helpers, recent-auth checks, header middleware behavior, and client-dimension metric labeling where applicable
- integration tests must verify session revocation, telemetry emission, and safe failure behavior under PostgreSQL-backed flows
- e2e tests must cover protected action step-up, session revocation flow, built-in UI security header presence, and at least one client-distinguishable observability path if surfaced externally
- regression tests must prove ordinary authenticated CRUD and admin flows remain functional

## Build order
1. add session security and step-up primitives
2. add rate limiting and security header middleware
3. add metrics hooks and observability integration
4. extend auth and session endpoints
5. wire built-in UI security model
6. add fast tests
7. add integration tests
8. add e2e tests

---

# Phase 13 — Workflow, approvals, and reversible admin changes

## Objective
Support reviewable, staged, and reversible administrative changes for higher-risk operational environments.

## Locked
- Phase 0–12 public contracts and security invariants
- audit, history, policy, jobs, and hardening semantics
- tenant isolation and protected-field restrictions

## Stable
- dynamic CRUD core
- action execution framework
- history endpoints
- built-in UI core navigation and form rendering
- external-client contract

## Open
- approval workflow model
- draft and review flow
- rollback and revert helpers
- scheduled activation or publish flow if needed
- tests for reviewable change management

## Deliverables
- new `models/change_request.py`
- new `schemas/change_request.py`
- new `services/workflow.py`
- new `routers/workflow.py`
- extend history or audit correlation where needed
- built-in UI support for review, approve, reject, and revert flows where appropriate
- tests for workflow and reversible change semantics

## Hard requirements
- workflow support must be optional per model or action and driven by explicit admin metadata
- reviewed changes must record requester, reviewer, timestamps, decision, and reason where applicable
- approval and rejection actions must be policy-gated and auditable
- draft or staged changes must not silently bypass existing validation, readonly, protected-field, or tenant restrictions
- revert or rollback support must be limited to safe, explicit, auditable paths
- scheduled or deferred activation, if supported, must remain auditable and permission-checked
- built-in UI and external clients must be able to discover workflow requirements through metadata or capability endpoints
- workflow failures must return explicit validation or authorization errors

## Acceptance criteria
- a configured model or action can require approval before applying a state-changing operation
- a reviewer can approve or reject a pending change with an auditable reason path where configured
- a rejected change is not applied
- a reverted change creates a new auditable event rather than mutating history invisibly
- metadata and capability responses expose whether approval or revert flows are available
- all Phase 0–12 tests still pass unchanged
- all new Phase 13 tests pass

## Tests
- fast required
- integration required
- e2e required
- fast tests must cover workflow state transitions, approval gating, and metadata exposure
- integration tests must verify pending-change persistence, approval application, rejection behavior, and revert audit linkage under PostgreSQL
- e2e tests must cover submit-for-review, approve, reject, and revert flows
- regression tests must prove models without workflow enabled continue to behave normally

## Build order
1. add workflow models and schemas
2. add workflow service and policy integration
3. extend metadata and capability exposure for workflow
4. add workflow endpoints and built-in UI flows
5. add fast tests
6. add integration tests
7. add e2e tests

---

# Phase 14 — Enterprise client and multi-surface delivery

## Objective
Add a separate enterprise-grade external client surface such as Flutter while keeping the built-in UI lightweight and the shared admin contract authoritative.

## Locked
- Phase 0–13 public contracts and security invariants
- built-in UI remains optional and lightweight by design
- admin contract endpoints remain the source of truth for all clients
- tenant, audit, impersonation, break-glass, policy, jobs, workflow, and hardening semantics

## Stable
- built-in UI renderer and support matrix
- contract versioning and deprecation rules
- external-client-facing metadata endpoints
- auth and admin context endpoints may be extended minimally for enterprise-client usability

## Open
- enterprise client integration guidance
- client-specific capability negotiation
- richer widget mapping for advanced clients
- multi-surface compatibility testing
- enterprise-client support policy
- optional file and attachment UX contract refinements

## Deliverables
- explicit multi-client compatibility guidance for built-in UI versus enterprise client responsibilities
- optional enterprise client capability negotiation via `/admin/client-config` or equivalent
- extend contract schemas for advanced renderer hints where safe and additive
- optional attachment and file-field metadata refinements for enterprise clients if file handling is in scope
- compatibility documentation for built-in UI, enterprise Flutter client, and API-only usage
- tests for multi-surface compatibility and advanced-client readiness

## Hard requirements
- the enterprise client must consume the same core admin contract as the built-in UI
- enterprise-client additions must remain additive or versioned and must not silently break the lightweight built-in UI
- the built-in UI must not be forced into full feature parity with enterprise-only UX requirements
- client-specific enhancements must be expressed through explicit capabilities, widget hints, support matrices, or versioned contract extensions
- file, attachment, or artifact handling exposed to enterprise clients must remain permission-scoped, tenant-safe, and protected-field safe
- contract compatibility across multiple client surfaces must be release-testable

## Acceptance criteria
- an enterprise client can negotiate or consume the supported contract capabilities without built-in-UI assumptions
- built-in UI remains functional and lightweight after enterprise-client metadata extensions
- multi-surface compatibility documentation clearly states which flows are baseline, advanced, or client-specific
- advanced renderer hints do not leak protected or internal backend details
- all Phase 0–13 tests still pass unchanged
- all new Phase 14 tests pass

## Tests
- fast required
- integration required
- e2e recommended
- fast tests must cover advanced-client capability metadata, support-matrix consistency, and additive contract extension behavior
- integration tests must verify contract correctness under PostgreSQL, tenant-scoped, policy-enforced, job-enabled, and workflow-enabled scenarios for multiple client profiles
- e2e tests should cover one built-in UI flow and one enterprise-client-style metadata-driven flow against the same backend
- regression tests must prove built-in UI is not broken by enterprise-client extensions

## Build order
1. define built-in UI versus enterprise-client responsibility boundaries
2. extend capability negotiation and advanced renderer hints where needed
3. refine attachment or file metadata if in scope
4. write multi-surface compatibility documentation
5. add fast tests
6. add integration tests
7. add optional e2e compatibility tests

---

# Minimal meta-prompt template for any future phase

Use this when creating a new phase prompt.

## Objective
State the single main goal.

## Locked
List files or behaviors that must not change.

## Stable
List files or behaviors that may change only minimally.

## Open
List new files or areas allowed to evolve.

## Deliverables
List exact files and explicit extensions.

## Hard requirements
List the non-negotiable functional and security rules.

## Acceptance criteria
Use measurable statements only.

## Tests
State exactly which of fast, integration, and e2e are required.
State what must be covered and what regressions must remain green.

## Build order
Keep it short and execution-oriented.
