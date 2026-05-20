# Architecture

## Package layout

```text
adminfoundry/
  __init__.py                # public API: create_admin, ModelAdmin, CoreAdminConfig, AdminRegistry
  py.typed                   # PEP 561 marker

  core/
    app_factory.py           # create_admin() — config → AdminRuntime → FastAPI app
    config.py                # CoreAdminConfig dataclass + from_env()
    runtime.py               # AdminRuntime(config, db, registry)
    installers.py            # install_middleware, install_routes
    middleware.py            # RequestIDMiddleware, SecurityHeadersMiddleware
    errors.py                # consistent error envelope + handlers
    logging.py               # configure_logging (plain or JSON)
    health.py                # /healthz, /readyz

  db/
    session.py               # DatabaseManager (one engine, one sessionmaker)
    dependencies.py          # get_async_session — request-scoped session in a txn

  models/
    base.py                  # GlobalBase + TenantBase + GUID + Id/Timestamp mixins
    user.py, tenant.py, tenant_membership.py
    tenant_rbac.py           # tenant-LOCAL: TenantRole, TenantRolePermission, TenantMembershipRole
    permission_catalog.py, audit_log.py, impersonation_log.py

  auth/
    router.py                # POST /login, GET /me
    dependencies.py          # get_current_user, require_superadmin
    tokens.py                # JWT encode/decode, access + impersonation token types
    password.py              # bcrypt
    rate_limiter.py          # InMemoryLoginRateLimiter

  authz/
    permissions.py           # permission_key() + wildcard matcher
    dependencies.py          # require_permission
    catalog.py               # generate_permission_keys(registry) + sync_permission_catalog

  security/
    validation.py            # validate_{resource_name, action_name, tenant_slug, schema_name, permission_key, limit_offset}
    sanitize.py              # sanitize_payload(...) — secret redaction for logs/audit

  registry/
    registry.py              # AdminRegistry
    admin.py                 # ModelAdmin base class

  schemas/
    builder.py               # Dynamic Pydantic schemas + field-protection
    fields.py                # AdminModelSchema dataclass
    serialization/serializer.py

  contract/
    service.py               # build_model_contract(ModelAdmin) → ModelContractMeta
    router.py                # GET /_contract, /_contract/{resource}

  crud/
    router.py                # GET/POST/PATCH/DELETE /{resource}[/{record_id}]
    services.py, query.py, payload.py, errors.py, types.py

  actions/
    __init__.py              # AdminAction base + BulkDeleteAction
    router.py                # POST /{resource}/_actions/{action}

  tenancy/
    middleware.py            # TenantMiddleware (resolves slug → TenantContext)
    resolver.py              # slug extraction + cached lookup
    schema_strategy.py       # SET LOCAL search_path
    schema_names.py          # make_tenant_schema_name, validators
    bootstrap.py             # create_tenant_record, seed_default_tenant_roles, bootstrap_tenant
    context.py               # TenantContext, TenantAuthContext
    dependencies.py          # require_tenant_auth_context

  audit/
    service.py               # record_audit, record_audit_in_session, audit_payload, request_audit_kwargs

  root/
    router.py                # superadmin-only routes aggregator
    impersonation.py         # POST /root/impersonate
    users.py, tenants.py     # global user + tenant read endpoints

  builtins/
    admin.py, installer.py   # TenantRoleAdmin, TenantRolePermissionAdmin, TenantMembershipRoleAdmin

  cli/
    main.py                  # adminfoundry CLI (db, tenant, permissions, …)

  ui/
    router.py                # /admin shell routes
    templates/{app,login}.html
    static/admin/{admin.css, admin.js}
```

## Wiring (create_admin)

```text
CoreAdminConfig.from_env()
     │  validate()
     │  configure_logging()
     ▼
FastAPI()
     │  app.state.adminfoundry = AdminRuntime(config, db, registry)
     │  register_error_handlers(app)                # consistent envelope
     │  install_middleware(app, config)             # request_id ▸ security_headers ▸ cors ▸ tenant
     │  install_builtin_admins(registry)            # tenant_roles, tenant_role_permissions, tenant_membership_roles
     │  register(registry)                          # user-supplied
     │  install_routes(app, config)                 # /healthz ▸ /auth ▸ /admin/_contract ▸ /root ▸ /admin (UI+static) ▸ /admin/_actions ▸ /admin/{resource}
     ▼
app
```

## Request lifecycle

```text
Request
  │
  ▼  RequestIDMiddleware       request.state.request_id
  ▼  SecurityHeadersMiddleware adds X-Content-Type-Options, Referrer-Policy, X-Frame-Options
  ▼  CORSMiddleware            only if cors_origins configured
  ▼  TenantMiddleware          extracts slug → request.state.tenant: TenantContext
  ▼  Route handler             Depends(get_async_session) opens a txn-scoped session
  │                            Depends(require_tenant_auth_context) issues SET LOCAL search_path
  │                                and loads tenant-local roles + permission_keys
  │                            Permission check via TenantAuthContext.has_permission()
  │                            Body validation via Pydantic + clean_write_payload
  │                            Audit via record_audit_in_session (savepoint-isolated)
  ▼  Response                  envelope on errors; X-Request-ID echoed
```

## Runtime state (no globals)

Everything is reachable through one attribute on the FastAPI app:

```python
runtime = request.app.state.adminfoundry          # AdminRuntime
runtime.config                                    # CoreAdminConfig
runtime.db                                        # DatabaseManager
runtime.registry                                  # AdminRegistry
```

No module-level engine, no module-level settings singleton, no module-level
`admin_site`. The framework can run multiple `create_admin()` apps in the
same Python process without state leaking between them.
