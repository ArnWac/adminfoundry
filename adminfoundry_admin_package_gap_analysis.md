# adminfoundry — Gap Analysis für ein gutes Admin-Package

## Zielbild

`adminfoundry` soll nicht nur ein CRUD-Generator sein, sondern ein echtes, erweiterbares Admin-Package für FastAPI-Anwendungen.

Der wichtigste Architekturpunkt: Das Package darf nicht fest an ein internes User-, Auth- oder Permission-Modell gekoppelt sein. Stattdessen sollte `create_admin()` Provider akzeptieren, damit Projekte eigene Authentifizierung, eigene User-Modelle und eigene Berechtigungslogik integrieren können.

```python
app = create_admin(
    config=CoreAdminConfig(...),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
)
```

Optional später:

```python
app = create_admin(
    config=CoreAdminConfig(...),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
    permission_provider=MyPermissionProvider(),
    tenant_provider=MyTenantProvider(),
)
```

---

## 1. Provider-Schicht als zentrales Architekturziel

### Problem

Wenn Router, CRUD-Logik oder UI-Contracts direkt auf interne Klassen wie `User`, `Tenant`, `Role` oder konkrete JWT-Funktionen zugreifen, wird `adminfoundry` schwer in bestehende Projekte integrierbar.

Ein gutes Admin-Package muss folgende Szenarien unterstützen:

- eigenes SQLAlchemy-User-Modell
- bestehende FastAPI-Auth
- externe Auth-Systeme wie Keycloak, Authentik, Auth0, Supabase oder Appwrite
- Session-Cookies statt JWT
- interne Admin-User für kleine Projekte
- Multi-Tenant-User mit projektabhängiger Rechteprüfung

### Empfehlung

Auth, User, Permissions und Tenants sollten getrennt werden.

```python
class AuthProvider(Protocol):
    async def authenticate_request(self, request: Request) -> AuthIdentity | None:
        ...

    async def login(self, credentials: LoginCredentials) -> AuthSession:
        ...

    async def logout(self, request: Request) -> None:
        ...
```

```python
class UserProvider(Protocol):
    async def get_by_id(self, user_id: str) -> AdminUser | None:
        ...

    async def get_display_name(self, user: AdminUser) -> str:
        ...

    async def list_users(self, query: UserQuery) -> Page[AdminUser]:
        ...
```

```python
class PermissionProvider(Protocol):
    def is_superadmin(self, user: AdminUser) -> bool:
        ...

    def can(
        self,
        user: AdminUser,
        action: str,
        resource: str,
        obj: Any | None = None,
        ctx: AdminContext | None = None,
    ) -> bool:
        ...
```

```python
class TenantProvider(Protocol):
    async def resolve_tenant(self, request: Request) -> AdminTenant | None:
        ...
```

### Ziel

`adminfoundry` sollte intern nur noch gegen neutrale Admin-Abstraktionen arbeiten:

```python
@dataclass
class AdminUser:
    id: str
    email: str | None = None
    display_name: str | None = None
    is_active: bool = True
    is_superadmin: bool = False
```

```python
@dataclass
class AuthIdentity:
    user_id: str
    claims: dict[str, Any]
```

```python
@dataclass
class AdminTenant:
    id: str
    slug: str
    name: str | None = None
```

---

## 2. `create_admin()` als zentrale Integrationsstelle

### Empfohlene API

```python
app = create_admin(
    config=CoreAdminConfig(...),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
)
```

### Erweiterte Variante

```python
app = create_admin(
    config=CoreAdminConfig(...),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
    permission_provider=MyPermissionProvider(),
    tenant_provider=MyTenantProvider(),
)
```

### Built-in Default für Quickstart

Für kleine Projekte sollte weiterhin ein interner Default möglich sein:

```python
app = create_admin(
    config=CoreAdminConfig(
        auth_mode="builtin",
        database_url="sqlite+aiosqlite:///./admin.db",
    )
)
```

Aber intern sollte auch dieser Default nur ein Provider sein:

```python
auth_provider = BuiltinJWTAuthProvider(...)
user_provider = BuiltinSQLAlchemyUserProvider(...)
permission_provider = BuiltinRBACPermissionProvider(...)
```

### Harte Architekturregel

Router, CRUD-Services, Contract-Builder und UI dürfen nicht direkt auf konkrete Framework-Models zugreifen.

Schlecht:

```python
from adminfoundry.auth.dependencies import get_current_user
from adminfoundry.models import User
```

Besser:

```python
ctx = await admin_context_provider.from_request(request)
user = ctx.user
```

---

## 3. `AdminContext` einführen

Viele spätere Features werden einfacher, wenn alle Operationen denselben Kontext bekommen.

```python
@dataclass
class AdminContext:
    request: Request | None
    user: AdminUser | None
    tenant: AdminTenant | None
    source: Literal["ui", "api", "import", "job"]
    action: str | None = None
```

Dieser Context sollte verwendet werden in:

- CRUD-Operationen
- Lifecycle Hooks
- Permission Checks
- Field Policies
- Record Filtering
- Audit Logs
- Import/Export
- Jobs
- Admin Actions
- Contract API

---

## 4. Inline Models als eigenes Konzept

### Problem

`inline_fields` ist als Konzept zu schwach. Es beschreibt nur, dass ein Feld inline angezeigt werden könnte. Für echte Admin-Funktionalität braucht man aber ein eigenes Inline-Modell mit eigener Semantik.

### Empfehlung

Einführen von `InlineAdmin`:

```python
class CommentInline(InlineAdmin):
    model = Comment
    fk_name = "post_id"
    fields = ["author", "body", "is_public"]
    readonly_fields = ["created_at"]
    extra = 1
    can_delete = True
    ordering = ["created_at"]
```

Verwendung im Parent-Admin:

```python
class PostAdmin(ModelAdmin):
    model = Post
    inlines = [CommentInline]
```

### Backend-Semantik

Inline Models sind nicht nur UI. Sie benötigen transaktionale Backend-Logik:

```text
Parent create/update transaction
├── validate parent
├── validate inline rows
├── create/update/delete inline children
├── enforce tenant rules
├── enforce permissions
├── write audit diff for parent and children
└── rollback all if one inline operation fails
```

### Mindestfunktionen für V1/V1.1

- `InlineAdmin.model`
- `InlineAdmin.fk_name`
- `fields`
- `readonly_fields`
- `can_delete`
- `extra`
- `max_num`
- `ordering`
- Permission Checks pro Inline
- Contract-Ausgabe für UI

---

## 5. Field Registry / Field Adapter System

### Problem

Ein Admin-Package darf nicht nur SQLAlchemy-Spalten introspektieren. Es braucht eine Schicht, die aus Modellfeldern echte Admin-Felder macht.

### Empfehlung

```python
class FieldAdapter(Protocol):
    def supports(self, model_attr: Any) -> bool:
        ...

    def build_contract(self, field: Any, ctx: AdminContext) -> FieldContract:
        ...

    def serialize(self, value: Any, ctx: AdminContext) -> Any:
        ...

    def parse(self, value: Any, ctx: AdminContext) -> Any:
        ...
```

### Wichtige Feldtypen

- `StringField`
- `TextAreaField`
- `MarkdownField`
- `RichTextField`
- `BooleanField`
- `DateTimeField`
- `EnumField`
- `MoneyField`
- `JSONField`
- `FileField`
- `ImageField`
- `ForeignKeyField`
- `ManyToManyField`
- `HasManyInlineField`
- `ComputedField`
- `ReadOnlyField`
- `SecretField`

### Warum wichtig?

Ohne Field Registry entstehen später viele Sonderfälle in:

- Schema Builder
- Serializer
- Contract API
- UI Renderer
- Import/Export
- Validation
- Permissions

---

## 6. Contract API versionieren

Wenn `adminfoundry` renderer-unabhängig sein soll, muss der Contract stabil und explizit sein.

### Beispiel

```json
{
  "contract_version": "1.0",
  "resource": "posts",
  "label": "Posts",
  "capabilities": {
    "create": true,
    "update": true,
    "delete": false,
    "bulk_actions": ["publish", "archive"]
  },
  "fields": [
    {
      "name": "title",
      "type": "string",
      "required": true,
      "widget": "text",
      "readonly": false,
      "help_text": "Public post title"
    }
  ],
  "relations": [],
  "inlines": [],
  "fieldsets": [],
  "filters": [],
  "ordering": []
}
```

### Muss enthalten

- Contract-Version
- Ressourcen-Metadaten
- Capabilities
- Felder
- Feldrechte
- Widgets
- Validierungsregeln
- Fieldsets
- Filter
- Actions
- Relations
- Inlines
- List View Definition
- Detail View Definition

---

## 7. Lifecycle Hooks mit Context

### Empfehlung

```python
class ModelAdmin:
    async def before_validate(self, data: dict, ctx: AdminContext) -> dict:
        return data

    async def validate_create(self, data: dict, ctx: AdminContext) -> None:
        ...

    async def before_create(self, data: dict, ctx: AdminContext) -> dict:
        return data

    async def after_create(self, obj: Any, ctx: AdminContext) -> None:
        ...

    async def validate_update(self, obj: Any, data: dict, ctx: AdminContext) -> None:
        ...

    async def before_update(self, obj: Any, data: dict, ctx: AdminContext) -> dict:
        return data

    async def after_update(self, obj: Any, changes: dict, ctx: AdminContext) -> None:
        ...

    async def before_delete(self, obj: Any, ctx: AdminContext) -> None:
        ...

    async def after_delete(self, obj: Any, ctx: AdminContext) -> None:
        ...
```

### Wichtig

Hooks sollten für alle Quellen gleich funktionieren:

- Admin UI
- REST API
- Import
- Bulk Actions
- Jobs
- Webhooks

---

## 8. Policy-System vereinheitlichen

### Problem

Wenn `admin_only`, `access_roles`, `field_policies`, `record_access`, `action_policies` und `AuthProvider.is_superadmin()` parallel existieren, wird das Rechte-System schwer nachvollziehbar.

### Empfehlung

Eine zentrale Policy-Schicht:

```python
class AdminPolicy:
    def can_view_model(self, user: AdminUser, ctx: AdminContext) -> bool:
        ...

    def can_create(self, user: AdminUser, ctx: AdminContext) -> bool:
        ...

    def can_view_object(self, user: AdminUser, obj: Any, ctx: AdminContext) -> bool:
        ...

    def can_update_object(self, user: AdminUser, obj: Any, ctx: AdminContext) -> bool:
        ...

    def can_delete_object(self, user: AdminUser, obj: Any, ctx: AdminContext) -> bool:
        ...

    def field_permission(
        self,
        user: AdminUser,
        field: str,
        obj: Any | None,
        ctx: AdminContext,
    ) -> FieldPermission:
        ...
```

Komfort-Konfigurationen wie `admin_only=True` dürfen bleiben, sollten aber intern in Policies übersetzt werden.

---

## 9. User-Management als austauschbares Modul

### Ziel

`adminfoundry` sollte zwei Modi unterstützen:

```python
CoreAdminConfig(
    user_mode="builtin",
)
```

und:

```python
CoreAdminConfig(
    user_mode="external",
)
```

### Built-in Mode

Geeignet für kleine Projekte und Quickstarts.

```python
app = create_admin(
    config=CoreAdminConfig(user_mode="builtin")
)
```

### External Mode

Geeignet für reale Anwendungen mit bestehender Authentifizierung.

```python
app = create_admin(
    config=CoreAdminConfig(user_mode="external"),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
)
```

Optional mit Permissions und Tenancy:

```python
app = create_admin(
    config=CoreAdminConfig(user_mode="external"),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
    permission_provider=MyPermissionProvider(),
    tenant_provider=SubdomainTenantProvider(),
)
```

### Klare Regel

Das interne `User`-Modell darf ein Default sein, aber keine harte Voraussetzung.

---

## 10. Admin Actions stärker typisieren

### Problem

Actions als lose Dicts werden schnell unübersichtlich.

### Empfehlung

```python
class PublishAction(AdminAction):
    name = "publish"
    label = "Publish selected"
    confirm = True
    bulk = True
    input_schema = PublishActionInput

    async def run(self, objects: list[Any], data: PublishActionInput, ctx: AdminContext):
        ...
```

### Vorteile

- typisierte Action-Parameter
- automatische Form-Generierung
- Validation
- Permission Checks
- Audit Log
- optional async Job Execution
- Progress Tracking
- Partial-Success Handling

---

## 11. Form Layout API ausbauen

### Empfehlung

```python
class PostAdmin(ModelAdmin):
    fieldsets = [
        Fieldset("Content", fields=["title", "slug", "body"]),
        Fieldset("Publishing", fields=["status", "published_at"]),
        Fieldset("SEO", fields=["seo_title", "seo_description"], collapsed=True),
    ]
```

### Spätere Erweiterungen

- Tabs
- Collapsible Sections
- Side Panels
- Readonly Detail Panels
- Conditional Fields
- Dependent Fields
- Help Text
- Placeholders
- Custom Components

---

## 12. List View Features

Bereits vorhandene oder naheliegende Konzepte wie `list_display`, `search_fields`, `filter_fields`, `ordering` und `list_editable` sind gut, aber für produktive Admin-Oberflächen fehlen vermutlich:

- saved filters
- custom filters
- date hierarchy
- column visibility
- export current filtered view
- bulk edit
- row-level actions
- custom row badges
- user-specific list density
- default ordering per user
- full-text-search backend adapter

Besonders wertvoll für Alltagseinsatz:

1. Saved Filters
2. Custom Filters
3. Row Actions
4. Export der aktuell gefilterten Ansicht
5. Column Visibility

---

## 13. Vorgeschlagene Modulstruktur

```text
adminfoundry/
  providers/
    __init__.py
    auth.py
    users.py
    permissions.py
    tenants.py

  admin/
    context.py
    inline.py
    policy.py
    lifecycle.py
    actions.py

  fields/
    __init__.py
    base.py
    registry.py
    scalar.py
    relation.py
    files.py

  contracts/
    __init__.py
    version.py
    resource.py
    fields.py
    actions.py
    inlines.py
```

---

## 14. Priorisierung

### P0 — Vor V1 wichtig

| Priorität | Feature | Grund |
|---:|---|---|
| 1 | Provider-Schicht für Auth/User/Permissions/Tenants | verhindert harte Kopplung an interne Models |
| 2 | `AdminContext` | Grundlage für Hooks, Permissions, Audit und Tenancy |
| 3 | Field Registry / Field Adapter | Grundlage für saubere Forms, Relations und Contract API |
| 4 | Contract API versionieren | wichtig für Built-in UI und spätere externe UIs |
| 5 | Policy-System vereinheitlichen | verhindert inkonsistente Rechteprüfung |

### P1 — Sehr wertvoll nach stabiler Basis

| Feature | Grund |
|---|---|
| `InlineAdmin` | notwendig für Django-ähnliche Admin-Qualität |
| Typed Admin Actions | wichtig für Jobs, Workflows und Bulk Actions |
| Custom Filters / Saved Filters | hoher Nutzen im Alltag |
| Form Layout API | wichtig für komplexere Business-Objekte |
| Custom Pages / Plugin Slots | wichtig für Dashboard und Extensions |

### P2 — Später

| Feature | Einschätzung |
|---|---|
| OIDC/SAML/SCIM | Enterprise, aber Provider-Schnittstellen jetzt vorbereiten |
| Workflow Approvals | späteres Enterprise-Feature |
| White Labeling | später |
| Billing/Metering | parken |
| Flutter UI | erst nach stabiler Contract API sinnvoll |

---

## 15. Kritische Architekturentscheidung

Die wichtigste Entscheidung ist nicht, ob `adminfoundry` noch mehr Features bekommt.

Die wichtigste Entscheidung ist:

> Wird `adminfoundry` ein Framework mit eigenem Auth-/User-System oder ein Admin-Package, das sich sauber in bestehende Anwendungen einfügt?

Für ein gutes Package ist die zweite Richtung stärker.

Daher sollte die nächste Entwicklungsphase nicht primär neue Features bauen, sondern diese Grundlagen stabilisieren:

1. `create_admin()` nimmt Provider entgegen.
2. Router und Services arbeiten nur noch mit `AdminContext`.
3. Internes User/Auth-System wird zu einem Default-Provider degradiert.
4. Permissions laufen über eine zentrale Policy-Schicht.
5. Field/Relation/Inline-Logik wird aus dem Schema Builder herausgezogen.

---

## 16. Konkrete nächste Aufgabe für Claude Code

### Ziel

Refactor vorbereiten, damit `adminfoundry` externe Auth- und User-Systeme unterstützt.

### Auftrag

```text
Refactor adminfoundry so that create_admin() accepts optional provider instances:

- auth_provider
- user_provider
- permission_provider
- tenant_provider

Introduce neutral provider protocols and an AdminContext object.
Do not remove the existing built-in auth/user functionality yet. Instead, wrap the current implementation behind default providers.

Hard requirements:
- Routers must no longer directly depend on concrete User models where avoidable.
- Request handling should resolve an AdminContext once and pass it into CRUD, contract, permission and audit paths.
- Built-in auth remains the default for quickstart usage.
- External provider mode must be possible via:

app = create_admin(
    config=CoreAdminConfig(...),
    auth_provider=MyAppAuthProvider(),
    user_provider=MyAppUserProvider(),
)

- Add tests for built-in mode and external provider mode.
- Do not add OIDC/SAML yet.
- Do not add InlineAdmin yet, but design AdminContext and provider interfaces so InlineAdmin can use them later.
```

### Acceptance Criteria

- `create_admin(config=...)` still works with built-in defaults.
- `create_admin(config=..., auth_provider=..., user_provider=...)` works.
- A route can access `ctx.user` without importing the concrete internal `User` model.
- Permission checks go through `PermissionProvider` or a central policy abstraction.
- Existing tests still pass or are intentionally updated.
- New tests cover at least one fake external auth/user provider.
