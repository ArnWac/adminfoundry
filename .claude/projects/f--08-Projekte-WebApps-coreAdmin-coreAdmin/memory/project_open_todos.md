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

4. **Permission-Matrix pro Rolle (Standard-Rollen)** — Neues Modell `RolePermission(role_id, model_name, can_list, can_create, can_update, can_delete)`. `PolicyEngine` schaut statt in `ModelAdmin`-Config in die DB. Im Admin-UI konfigurierbar. Aktuell hat `Role` nur ein `name`-Feld ohne attached Permissions — `PolicyEngine` prüft Rollennamen gegen manuell definierte `access_roles` auf `ModelAdmin`.

5. **Field-level Permissions** — Aktuell nur protected/not-protected. Braucht `has_change_permission(obj)` pro Feld/Objekt analog zu Django.

5. **Custom Filters** — Aktuell nur Boolean-Filter. Fehlen: Range-Filter (Datum, Zahl), Enum-Filter, Relation-Filter (z.B. "nur User von Tenant X").

## UI / UX

6. **Inline-Relations** — ForeignKey/M2M direkt im Detail-Formular bearbeiten (z.B. User + Roles im User-Formular), ohne separate Seite.

7. **List-Editable** — Felder direkt in der Listenansicht inline editieren.

8. **Audit Log im UI** — `AuditLog`-Modell existiert, ist aber nirgends in der Admin-UI sichtbar.

9. **Breadcrumb-Navigation** — Fehlt im aktuellen UI vollständig.

10. **Dark Mode** — Rein CSS-seitig, kleiner Aufwand.

## Ops / Observability

11. **Health-Dashboard** — DB-Status, Queue-Länge, letzte Jobs, Rate-Limit-Hits auf einer Seite aggregiert.

12. **Metrics-Endpoint** — `GET /metrics` im Prometheus-Format (aktive Sessions, Job-Fehlerrate, Rate-Limit-Hits, etc.).

13. **CSV/Excel Export** — JSON-Export läuft bereits; CSV/XLSX ist für Ops-Workflows deutlich häufiger gefragt.
