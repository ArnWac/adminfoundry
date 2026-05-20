# adminfoundry v1 — Fahrplan nach Core / Security / Extensions

## Leitlinie

Der Core darf nur das enthalten, was jede adminfoundry-App braucht und was den Pfad stabilisiert:

```text
Registry
-> Contract
-> CRUD
-> TenantAuthContext
-> Permission Keys
-> Minimal UI
```

Alles, was nur manche Apps brauchen, gehört in Extensions. Alles, was Compliance, Enterprise oder komplexe Policies betrifft, kommt nach v1.

---

# 1. Core — muss in v1-MVP

Diese Dinge bilden das eigentliche Framework-Fundament.

## Phase C0 — Core stabilisieren

**Ziel:** Keine alten Konzepte mehr im aktiven Code.

Muss wegbleiben:

```text
admin_site
settings.py singleton
AuthProvider
Role / RolePermission
user_roles / membership_roles
PolicyEngine
get_db / get_admin_db
AsyncSessionLocal
ExtensionRegistry
DashboardRegistry
EventBus
```

**Core-Struktur:**

```text
core/
db/
auth/
authz/
registry/
schemas/
crud/
contract/
tenancy/
builtins/
ui/
```

**Akzeptanz:**

```text
create_admin() läuft
Package importiert sauber
pytest läuft grün
grep checks auf Legacy-Begriffe sind sauber
```

---

## Phase C1 — Registry + ModelAdmin

**Kategorie:** Core

Enthält:

```text
AdminRegistry
ModelAdmin
resource name
list_display
search_fields
ordering
readonly_fields
hidden/protected fields
actions declaration
computed/calculated fields declaration
```

**Legacy-Alternative:**

| Alt | Neu |
|---|---|
| `admin_site` | `runtime.registry` |
| globale Registrierung | `register(registry)` Callback |
| riesiger `ModelAdmin` mit vielen Flags | kleiner `ModelAdmin`, Features später modular |

**Nicht jetzt:**

```text
inline_fields
requires_approval
allow_import
widget_overrides
field_policies
record_filter
```

---

## Phase C2 — Schema Builder + Serializer

**Kategorie:** Core

Muss können:

```text
SQLAlchemy-Felder erkennen
Primary Key erkennen
readonly markieren
hidden/protected ausblenden
computed fields serialisieren
einzelnen Record serialisieren
Listen serialisieren
keine Secrets leaken
```

**Wichtig für Security:**

```text
hashed_password nie serialisieren
hidden_fields nie serialisieren
read_only fields nie writable
```

---

## Phase C3 — Contract API

**Kategorie:** Core

Endpoints:

```text
GET /api/v1/admin/_contract
GET /api/v1/admin/_contract/{resource}
```

Liefert:

```text
resources
fields
actions
list_display
search_fields
ordering
readonly/hidden metadata
computed field metadata
```

**Warum wichtig?**

Die UI und externe Clients hängen daran. Ohne stabilen Contract wird dein Admin wieder server-template-lastig und schwer erweiterbar.

**Legacy-Alternative:**

| Alt | Neu |
|---|---|
| `capabilities.py` | Contract-Service |
| `navigation.py` | Contract + UI filtert |
| `client_config.py` | kleiner Contract |
| `ui_renderer.py` | später UI-Hints |

---

## Phase C4 — CRUD API

**Kategorie:** Core

Endpoints:

```text
GET    /api/v1/admin/{resource}
POST   /api/v1/admin/{resource}
GET    /api/v1/admin/{resource}/{id}
PATCH  /api/v1/admin/{resource}/{id}
DELETE /api/v1/admin/{resource}/{id}
```

Muss können:

```text
pagination
limit/offset bounds
basic search
ordering
PK coercion UUID/int/str
unknown field rejection
readonly/hidden write rejection
is_system delete guard
permission-key checks
```

**Nicht im Core-CRUD:**

```text
CSV import
export
upload
soft delete
restore
hard delete
bulk import
workflow approval
record policies
```

---

## Phase C5 — Auth + Authz

**Kategorie:** Core

Auth:

```text
password hashing
JWT access token
token_version check
inactive user rejection
require_superadmin
impersonation token detection
```

Authz:

```text
permission_key()
has_permission()
assert_permission()
require_permission()
```

Permission Keys:

```text
admin.project.list
admin.project.read
admin.project.create
admin.project.update
admin.project.delete
admin.project.archive
admin.project.*
admin.*
```

**Legacy-Alternative:**

| Alt | Neu |
|---|---|
| `RolePermission.can_list` | `admin.<resource>.list` |
| `RolePermission.can_create` | `admin.<resource>.create` |
| `action_policies` | `admin.<resource>.<action>` |
| `tenant_admin` role-name checks | permission keys |

---

## Phase C6 — Tenancy

**Kategorie:** Core, wenn Multi-Tenant Ziel bleibt

Global/public:

```text
User
Tenant
TenantMembership
PermissionCatalog
AuditLog
ImpersonationLog
```

Tenant-local:

```text
TenantRole
TenantRolePermission
TenantMembershipRole
```

Muss können:

```text
Tenant per Header/Subdomain resolven
TenantMembership prüfen
tenant-local Rollen laden
permission_keys laden
SET LOCAL search_path setzen
gleiche DB-Session für AuthContext + CRUD nutzen
```

**Nicht wieder einführen:**

```text
row-level tenancy
tenant_id injection
_tenant_filter
per-tenant engine cache
tenant-specific sessions
Role.tenant_id = NULL
```

---

## Phase C7 — Built-in Admins

**Kategorie:** Core, aber minimal

In `builtins/` gehören nur tenant-lokale Admins:

```text
TenantRoleAdmin
TenantRolePermissionAdmin
TenantMembershipRoleAdmin
```

Nicht:

```text
UserAdmin
TenantAdmin
AuditLogAdmin
PermissionCatalogAdmin
```

Diese gehören später in Root Admin, nicht in Tenant CRUD.

---

## Phase C8 — Minimal UI Shell

**Kategorie:** Core, aber dünn

Server-Routen:

```text
/admin/login
/admin/dashboard
/admin/{resource}
...
```

Rendern nur:

```text
app.html
login.html
```

Daten kommen aus:

```text
Contract API
CRUD API
Auth API
```

Nicht im Core-UI:

```text
dashboard widgets
preferences persistence
password reset views
renderer support matrix
serverseitige Model-Labels
```

---

# 2. Core-nahe Security — in v1-MVP aufnehmen

Security ist keine Extension. Sie muss klein, testbar und früh im Core verankert sein.

## Phase S1 — Input Validation

**Kategorie:** Core Security

Validieren:

```text
resource names
action names
tenant slugs
schema names
permission keys
pagination params
ordering fields
search fields
payload fields
primary keys
```

Empfohlenes Modul:

```text
security/
  validation.py
  sanitize.py
```

Alternative:

```text
core/validation.py
```

Ich würde `security/` nehmen.

---

## Phase S2 — Payload Sanitization

**Kategorie:** Core Security

Redact:

```text
password
current_password
new_password
hashed_password
token
access_token
refresh_token
secret
secret_key
authorization
cookie
```

Nutzen in:

```text
audit
logging
error handling
debug output
```

---

## Phase S3 — Login Rate Limiter

**Kategorie:** Core Security MVP

In-memory reicht erstmal:

```text
auth/rate_limiter.py
```

Grenzen offen dokumentieren:

```text
nicht multi-worker sicher
reset bei Neustart
kein Redis-Zwang
```

Redis später optional.

---

## Phase S4 — Token Version Revocation

**Kategorie:** Core Security

MVP-Konzept:

```text
JWT.tkv
User.token_version
```

Bei folgenden Events erhöhen:

```text
Passwort geändert
User deaktiviert
Superadmin-Status geändert
Security reset
```

Damit brauchst du noch keine Token-Blacklist für MVP.

---

## Phase S5 — Security Invariant Tests

**Kategorie:** Core Security

Tests:

```text
hidden fields never serialized
hashed_password never serialized
readonly fields not writable
inactive user rejected
token_version mismatch rejected
impersonation token rejected by require_superadmin
unknown permission denied
```

Zusätzlich: Grep-Test gegen Legacy-Begriffe.

---

# 3. Core-nah, aber nach MVP

Diese Features sind sinnvoll, aber erst nach stabilem Core.

## Phase N1 — Computed / Calculated Fields

**Kategorie:** Core-nah

Empfehlung:

```python
computed_fields = {
    "display_name": lambda obj: f"{obj.name} ({obj.id})"
}
```

Oder Django-like:

```python
calculated_fields = ("display_name",)

def display_name(self, obj):
    ...
```

Eine API wählen, nicht beide.

Muss gelten:

```text
im Contract sichtbar
im Serializer sichtbar
read-only
nicht writable
kein DB-Feld nötig
```

---

## Phase N2 — Admin Actions

**Kategorie:** Core-nah

Endpoint:

```text
POST /api/v1/admin/{resource}/_actions/{action}
```

Payload:

```json
{ "ids": ["..."] }
```

Auth:

```text
admin.<resource>.<action>
```

Nicht:

```text
background jobs
approval workflows
import/export
```

---

## Phase N3 — Minimal Audit Log

**Kategorie:** Core-nah, sicherheitsrelevant

Track:

```text
actor_user_id
tenant_id
resource
record_id
action
method
path
status_code
created_at
```

Events:

```text
login_success
login_failure
crud_create
crud_update
crud_delete
admin_action
impersonation_start
impersonation_stop
```

Regel:

```text
Audit failure must not fail main request.
```

---

## Phase N4 — Impersonation

**Kategorie:** Core-nah, aber erst nach Audit

Regeln:

```text
nur superadmin
token type = impersonation
enthält impersonated_by
kurze TTL
nicht renewable
require_superadmin lehnt Impersonation ab
Audit required
```

Zusätzlich sinnvoll:

```text
nicht inactive user impersonaten
nicht superadmin impersonaten, außer explizit erlaubt
tenant_id nur wenn Zieluser aktive Membership hat
```

---

## Phase N5 — Root Admin Context

**Kategorie:** Core-nah, aber getrennt vom Tenant-CRUD

Root/global models:

```text
User
Tenant
TenantMembership
PermissionCatalog
AuditLog
ImpersonationLog
```

Prefix:

```text
/api/v1/root
```

oder:

```text
/api/v1/admin/_root
```

Regeln:

```text
superadmin only
kein TenantAuthContext
kein search_path
impersonation token verboten
```

---

# 4. Extensions — später auslagern

Diese Features sind wertvoll, aber gehören nicht in den Core.

## Extension E1 — Import / Export

Alt:

```text
allow_import
allow_export
import_export extension
```

Warum wichtig:

```text
CSV/JSON/XLSX Export
Bulk Import
Dry Run
Fehlerreport
```

Warum Extension:

```text
Dateiformate
Validierung
Jobs
Audit
potenziell große Datenmengen
```

Alternative:

```text
extensions/import_export/
```

MVP im Core: nein.

---

## Extension E2 — Workflows / Approval

Alt:

```text
requires_approval
workflow extension
```

Warum wichtig:

```text
kritische Änderungen freigeben
4-Augen-Prinzip
Compliance
```

Warum Extension:

```text
State Machine
Reviewer
Notifications
Audit
ggf. Jobs
```

Alternative:

```text
extensions/workflows/
```

Core-Hook später:

```text
before_mutation
after_mutation
action execution hook
```

---

## Extension E3 — Webhooks

Warum wichtig:

```text
Integrationen
Event Delivery
externe Automationen
```

Warum Extension:

```text
Retry
HMAC Signing
Dead Letter
Delivery Logs
Security
```

Alternative:

```text
extensions/webhooks/
```

Braucht vorher:

```text
Audit/Event-Abstraktion
```

---

## Extension E4 — Jobs

Warum wichtig:

```text
lange Aktionen
Import/Export
Webhook Retry
Reports
```

Warum Extension:

```text
Queue Backend
Worker
Status Tracking
Retries
```

Alternative:

```text
extensions/jobs/
```

Nicht in Core.

---

## Extension E5 — Observability / Metrics

Warum wichtig:

```text
Admin-Nutzung
Fehlerquoten
Security Events
Performance
```

Warum Extension:

```text
Prometheus
Dashboard
Metriken
optionale Dependencies
```

Alternative:

```text
extensions/observability/
```

Core höchstens:

```text
structured log hooks
request_id
```

---

## Extension E6 — Dashboard / Widgets

Warum wichtig:

```text
Übersicht
Counts
Recent Activity
Security Alerts
Jobs
```

Warum Extension/UI-Modul:

```text
Widget-System koppelt an Metrics, Jobs, Audit
```

Alternative:

```text
extensions/dashboard/
```

oder später `dashboard/` als optionaler UI Layer.

---

## Extension E7 — Storage / S3

Warum wichtig:

```text
Uploads
Dateifelder
Import/Export Artefakte
Reports
```

Warum Extension/SPI:

```text
boto3 optional
Storage Backend austauschbar
```

Alternative:

```text
storage SPI im Core klein
S3 Provider in extensions/storage_s3
```

Für jetzt: Parken.

---

# 5. Post-v1 / Enterprise

Nicht jetzt bauen.

```text
2FA/TOTP
password reset by email
refresh tokens
session management
SCIM/SAML
OAuth providers
RootRole / RootPermission
field-level policies
record-level policies
inline editing
advanced filters
relationship filters
nested serialization
billing
usage metering
seat limits
white labeling
multi-region tenancy
Redis distributed cache
```

---

# 6. Spezifische Legacy-Features sortiert

| Legacy Feature | Kategorie | Warum wichtig? | Was tun? |
|---|---|---|---|
| `admin_site` | Architektur alt | Registry nötig | durch `runtime.registry` ersetzen |
| `settings.py` | Architektur alt | Config nötig | durch `CoreAdminConfig` ersetzen |
| `Role` | Architektur alt | Rollen nötig | durch `TenantRole` ersetzen |
| `RolePermission.can_*` | Architektur alt | Rechte nötig | durch Permission Keys ersetzen |
| `permission_matrix` | UI später | RBAC UX wichtig | später RBAC UI |
| `field_policies` | Post-v1 | sensible Felder | später Policy-Modul |
| `record_filter` | Post-v1 | row-level rules | später `get_queryset(ctx, stmt)` |
| `record_access` | Post-v1 | Objektzugriff | später Policy-Modul |
| `action_policies` | Core-nah | Actions schützen | durch Permission Keys lösen |
| `inline_fields` | Post-v1 | relationale UX | später Relation UI |
| `requires_approval` | Extension | Compliance | Workflows Extension |
| `allow_import` | Extension | Datenimport | Import/Export Extension |
| `widget_overrides` | Core-nah später | UI Hints | Contract UI hints |
| `computed_fields` | Core-nah | sehr nützlich | früh übernehmen |
| `password_reset_tokens` | Post-v1 Auth | Nutzerverwaltung | später Auth-Modul |
| `revoked_tokens` | Security später | einzelne Tokens sperren | nach token_version, DB-first |
| `webhooks` | Extension | Integrationen | später Webhook Extension |
| `dashboard widgets` | Extension/UI | Übersicht | später Dashboard Extension |
| `jobs` | Extension | lange Tasks | später Jobs Extension |
| `observability` | Extension | Monitoring | später Observability |
| `ui_preferences` | UI später | Komfort | localStorage oder später DB |
| `storage_s3` | Extension/SPI | Artefakte | später Storage SPI |

---

# 7. Empfohlener Gesamtfahrplan

## Milestone 1 — Clean Core Stabilization

```text
C0 Legacy raus
C1 Registry/ModelAdmin
C2 Schema Builder/Serializer
C3 Contract
C4 CRUD
C5 Auth/Authz
C6 Tenancy
C7 Builtins
S1 Input Validation
S2 Sanitization
S3 Rate Limiter
S4 Token Version Tests
```

Ergebnis:

```text
lauffähiger v1-Core ohne Feature-Ballast
```

---

## Milestone 2 — Usable Admin MVP

```text
Minimal UI Shell
Computed Fields
Admin Actions
Minimal Audit
```

Ergebnis:

```text
Admin ist praktisch nutzbar
```

---

## Milestone 3 — Support/Security MVP

```text
Impersonation
Root Admin Context
RevokedToken DB-first optional
Request ID
Security invariant tests
```

Ergebnis:

```text
sicherer Betrieb für interne/adminnahe Nutzung
```

---

## Milestone 4 — First Extension Wave

```text
Import/Export
Jobs
Webhooks
Workflows
Observability
Dashboard
Storage SPI/S3
```

Ergebnis:

```text
Produkt wird erweiterbar, ohne Core aufzublähen
```

---

## Milestone 5 — Enterprise/Post-v1

```text
Field Policies
Record Policies
Advanced Relationship UI
2FA
Password Reset
OAuth/SAML/SCIM
Billing/Metering
White Labeling
```

---

# 8. Konkrete nächste Reihenfolge

Baue als nächstes nicht Webhooks, Import/Export oder Dashboard.

Baue in dieser Reihenfolge:

```text
1. Core stabil
2. MVP Security
3. Contract final
4. CRUD/Authz final
5. Minimal UI
6. Computed Fields
7. Admin Actions
8. Audit
9. Impersonation
10. Root Admin
```

Erst danach Extensions.

Der wichtigste Architekturgrundsatz bleibt:

```text
Was jede adminfoundry-App braucht, kommt in den Core.
Was nur manche Apps brauchen, wird Extension.
Was Compliance/Enterprise-spezifisch ist, kommt nach v1.
```
