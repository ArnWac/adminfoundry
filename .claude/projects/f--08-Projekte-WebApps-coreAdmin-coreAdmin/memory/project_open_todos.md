---
name: Offene Todos
description: Bekannte Lücken und geplante Features die noch nicht implementiert sind
type: project
---

## Sicherheit / Auth

1. **Tenant `is_active` durchsetzen** — `DisableTenantAction` setzt `is_active = False`, aber adminfoundry blockiert Zugriffe inaktiver Tenants aktuell nicht. Muss in `TenantMiddleware` oder `AuthProvider` ausgewertet werden.

2. **2FA (TOTP)** — Time-based One-Time Password als optionales Auth-Feature. Klarer Vorteil gegenüber Django Admin, das kein built-in 2FA hat.

3. **IP-Allowlist per Tenant** — Ergänzt `is_active`-Enforcement; Zugang nur aus definierten IP-Ranges.

## Permissions / Daten

4. ✅ **Permission-Matrix pro Rolle** — `RolePermission(role_id, model_name, can_list, can_create, can_update, can_delete)` implementiert. `PolicyEngine.effective_model_caps()` nimmt jetzt optionalen `db_caps`-Override. Async-Helper `fetch_model_caps` / `fetch_all_model_caps` in `adminfoundry/authz/role_caps.py`. `RolePermissionAdmin` registriert. Tests in `tests/test_role_permissions.py`. Migration `0003_add_role_permissions.py`. **Offen:** `_check_model_access` in `router.py` prüft noch nicht die DB-Permissions (nur `effective_model_caps` tut es).

5. ✅ **Field-level Permissions (per-Record)** — `PolicyEngine.evaluate_field()` nimmt jetzt optionalen `record`-Parameter. ModelAdmin kann `field_permission(user, field_name, record) -> FieldPolicy | None` überschreiben. `update_object`-Route übergibt das Objekt an `evaluate_field`.

5. ✅ **Custom Filters** — `FilterBuilder.build_filters()` unterstützt jetzt `range_filter_fields` (`field__gte` / `field__lte`) und `enum_filter_fields` (`field__in=a,b,c`). Beide Attribute auf `ModelAdmin` definiert. Werden automatisch aus Query-Params ausgelesen.

## UI / UX

6. ✅ **Inline-Relations** — `inline_fields: list[str]` auf ModelAdmin (Relationship-Attributnamen). Contract liefert `inline_relations: list[InlineRelationMeta]`. Serializer gibt verschachtelte Objekte zurück. **Offen:** Volle UI-Darstellung im admin.js (Inline-Formular rendern, Speichern).

7. ✅ **List-Editable** — `list_editable: list[str]` auf ModelAdmin. Contract enthält `list_editable`-Feld. admin.js rendert `<input class="list-inline-input">` für editierbare Felder und speichert per blur → PATCH.

8. ✅ **Audit Log im UI** — `AuditLogAdmin` registriert in `admin_config.py`. Read-only, Filter auf `action`/`method`/`status_code`, Range-Filter auf `created_at`, Sortierung nach `-created_at`.

9. ✅ **Breadcrumb-Navigation** — `setBreadcrumb(parts)` Funktion in admin.js. `<nav id="breadcrumb">` in base.html. Breadcrumbs werden in initList, initDetail, initCreate, initUpdate gesetzt.

10. ✅ **Dark Mode** — CSS Custom Properties + `html[data-theme="dark"]`. System-Präferenz via `@media (prefers-color-scheme: dark)`. Manueller Toggle via Button in Sidebar-Footer. Präferenz in localStorage gespeichert.

## Locale / i18n

14. ✅ **Tenant-Locale → JS-Fallback-Chain** — Tenant-Locale-Felder (`timezone`, `language`, `date_format`) sind im Model vorhanden. Wenn Multi-Tenant aktiviert wird: per Middleware/API in `window.ADMIN_TENANT_LOCALE` einbetten, damit die JS-Fallback-Chain `user → tenant → app` vollständig funktioniert.

15. ✅ **i18n-Grundstruktur (ADMIN_STRINGS)** — Alle UI-Strings aus admin.js + Templates in ein zentrales `ADMIN_STRINGS`-Objekt auslagern. Übersetzungs-JSON-Dateien pro Sprache. Language-Preference als vierte Pref-Einstellung. Drei-Tier: App-Default → Tenant-Language → User-Language. Hängt von Tenant-Locale-Integration ab.

## Signals / Events (Hohe Priorität)

17. ✅ **Signals / Event-Hooks** — `adminfoundry/signals.py`. `connect()`, `disconnect()`, `@on()`, `emit()`, `clear()`. Async-first. Fired in admin router: `post_create`, `post_update`, `pre_delete`, `post_delete`. `post_login`/`post_logout` noch offen (Auth-Router). — Loose-Coupling-Mechanismus analog Django-Signals. Apps können auf Framework-Events reagieren ohne adminfoundry zu patchen. Kern-Events: `post_create`, `pre_delete`, `post_login`, `post_logout`, `post_password_change`, `tenant_created`. API: `adminfoundry.signals.connect("post_create", handler)` oder Dekorator `@on("post_create")`. Async-Handler bevorzugt.
**Why:** Größter Hebel für Erweiterbarkeit — simpletimes kann z.B. auf `post_create` von Shift reagieren ohne Router zu ändern.

## Caching (Hohe Priorität)

18. ✅ **Caching-Layer** — `adminfoundry/cache.py`. `InMemoryBackend` (default), `RedisBackend` (optional, `pip install redis`). `configure(url)`, `cache.get/set/delete/clear`. Konfigurierbar via `CoreAdminConfig(cache_backend="redis://...")`. — Einheitliche Cache-API analog Django `cache.get/set/delete`. Backends: In-Memory (default), Redis (optional). Genutzt intern für Rate-Limiting (aktuell kein persistenter Cache), Session-Lookups, Contract-Metadaten. API: `from adminfoundry.cache import cache; await cache.get(key)`. Backend konfigurierbar via `CoreAdminConfig(cache_backend="redis://...")`.
**Why:** Rate-Limiting skaliert aktuell nicht über mehrere Prozesse; Redis-Cache löst das ohne externe Abhängigkeit zu erzwingen.

## File Storage (Hohe Priorität)

19. ✅ **File Upload + Storage Backends** — `adminfoundry/storage.py`. `LocalStorage` (default), `S3Storage` (optional, `pip install boto3`). `POST /api/v1/admin/upload` Endpoint. `CoreAdminConfig(storage_backend=LocalStorage(...))`. `FileField` auf ModelAdmin noch offen. — `FileField` / `ImageField` Unterstützung in ModelAdmin. Storage-Backends: Local (default), S3-kompatibel (optional via `boto3`). Upload-Endpoint: `POST /admin/upload`. Konfigurierbar via `CoreAdminConfig(storage_backend=LocalStorage("/uploads"))`. Gebraucht für: Profilbilder, Dokumente, Import-Dateien.
**Why:** Praktisch jede App braucht File Uploads — aktuell komplett offen.

## DX / CLI (Mittlere Priorität)

20. ✅ **`adminfoundry migrate` CLI-Wrapper** — `migrate generate -m "msg"`, `migrate apply`, `migrate status`. Wrapper um Alembic-Befehle. — Wrapper um `alembic revision --autogenerate` + `alembic upgrade head`. Ziel: `adminfoundry migrate` statt manuellem Alembic-Aufruf. Django's `makemigrations` / `migrate` als Vorbild. Größter DX-Vorteil von Django gegenüber adminfoundry heute.
**Why:** Alembic-Befehle sind lang und fehleranfällig; ein einfacher Wrapper verbessert die Developer-Experience erheblich.

21. ✅ **Management Commands Framework** — Entry-Points via `adminfoundry.commands` Gruppe in `pyproject.toml`. Apps registrieren Commands: `[project.entry-points."adminfoundry.commands"] my_cmd = "myapp.cli:fn"`. CLI lädt diese automatisch beim Start. — Erweiterbar-Framework damit eigene Apps Commands registrieren können: `adminfoundry run my_command`. Analog Django's `management/commands/`. Realisierbar mit Typer-Plugin-System oder Entry-Points in pyproject.toml.
**Why:** Apps wie simpletimes brauchen eigene CLI-Commands (z.B. `generate-shifts`); aktuell kein Erweiterungspunkt.

## Server-Side i18n (Mittlere Priorität)

22. ✅ **Server-Side i18n** — `adminfoundry/i18n.py`. `t(key, lang, **vars)`. Kataloge: en, de, fr, es, pt. `set_default_language()`, `add_catalog()`. Email-Templates (Reset, Welcome) in allen Sprachen. Wird von `create_coreadmin` mit `default_language` konfiguriert. — Übersetzung von Emails, API-Fehlermeldungen, CLI-Output. Aktuell nur JS-seitig (Admin-UI). Server-Side: `_("Password reset")` mit Locale aus Tenant oder Request. Relevant wenn Package öffentlich wird und nicht-englische Fehlermeldungen erwartet werden.
**Why:** Emails und API-Fehler sind aktuell immer Englisch, egal was der Tenant als Sprache hat.

## Seed / Test Data (Mittlere Priorität)

23. ✅ **Fixtures / Seed Data Loader** — `adminfoundry/fixtures.py`. `load_fixture(path, session)` und `dump_fixture(model_name, session, path)`. JSON + YAML (PyYAML optional). CLI: `adminfoundry loaddata <file>`, `adminfoundry dumpdata <model> -o <file>`. — Deklarative Testdaten via YAML/JSON: `adminfoundry loaddata fixtures/initial.yaml`. Analog Django-Fixtures. Gebraucht für: Demo-Daten, Integrationstests, initiale Stammdaten. Alternative: Factory-Boy-Integration für Tests.
**Why:** Aktuell wird Seed-Data manuell im Lifespan-Block geschrieben (blog-Beispiel); kein standardisierter Weg.

## Erweiterbarkeit / Public Package

16. **Pluggable User-Model (Option B)** — `create_adminfoundry(app, config=CoreAdminConfig(user_model=MyUser))` ermöglichen. adminfoundry prüft das übergebene Model gegen ein `UserProtocol` (Pflichtfelder: `email`, `is_active`, `is_superadmin`, `id`). Eigene Models können zusätzliche Felder mitbringen. Notwendig wenn adminfoundry öffentlich publiziert wird und andere Entwickler ihre eigenen User-Models mitbringen wollen.
**Why:** User will das Package für eigene Apps nutzen (simpletimes etc.) — kurzfristig reicht SQLAlchemy-Vererbung oder extra Tabelle. Option B ist erst relevant bei öffentlicher Veröffentlichung.

## Ops / Observability

11. ✅ **Health-Dashboard** — `GET /health/dashboard` aggregiert DB-Status, aktive Sessions, Rate-Limit-Config, Metriken-Snapshot, letzte 5 Jobs.

12. ✅ **Metrics-Endpoint** — `GET /metrics` im Prometheus-Format (text/plain). Enthält: requests_total, request_errors_total, actions_total, action_errors_total, audit_write_failures_total, active_sessions.

13. ✅ **CSV/Excel Export** — `GET /api/v1/admin/{model}/export?format=csv|json|xlsx` (max 10k Zeilen). XLSX erfordert `pip install openpyxl` (optional dep). Respektiert alle Filter, Search, Ordering, Tenant- und Policy-Filter.
