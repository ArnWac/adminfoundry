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

4. **`_check_model_access` DB-Permissions** — `_check_model_access` in `router.py` prüft noch nicht die DB-Permissions (`RolePermission`-Tabelle). Nur `effective_model_caps()` tut es. Muss noch in die Route-Ebene integriert werden.

## UI / UX

5. **Inline-Relations UI** — `inline_fields` und Contract sind implementiert. Offen: Volle UI-Darstellung im admin.js (Inline-Formular rendern, Speichern).

## Signals / Events

6. **Signals `post_login` / `post_logout`** — Core-Signals (`post_create`, `post_update`, `pre_delete`, `post_delete`) sind implementiert und werden im Admin-Router gefeuert. Webhooks (`adminfoundry.webhooks`) ebenfalls implementiert (HMAC-SHA256, httpx, async). **Offen:** `post_login` und `post_logout` werden im Auth-Router noch nicht gefeuert.

## Soft-Delete / Recycle Bin

7. ✅ **Soft-Delete** — `SoftDeleteMixin` in `models/base.py` (`deleted_at`-Kolumne). `ModelAdmin(soft_delete=True)`. DELETE setzt `deleted_at` statt Hard-Delete. `GET ?trash=1` zeigt nur gelöschte Records. `POST /{model}/{id}/restore` stellt wieder her. `DELETE /{model}/{id}/hard` löscht permanent (Superadmin). UI: Papierkorb-Button in Listenansicht, Restore/Hard-Delete-Buttons im Trash-Modus.

   **DSGVO-Offen:**
   - **Anonymize-on-request**: PII-Felder in soft-deleted Records durch Platzhalter ersetzen (`anonymized@gdpr.invalid`).
   - **Retention Policy**: `soft_delete_retention_days` auf ModelAdmin — automatische Bereinigung nach X Tagen.
   - **Audit-Log-Anonymisierung**: GDPR-Delete-Workflow sollte E-Mail/Namen im Audit-Log pseudonymisieren.

## Erweiterbarkeit / Public Package

8. ✅ **Pluggable User-Model** — `CoreAdminConfig(user_model=MyUser)`. `AuthProvider.user_model` überschreibbar. `validate_user_model()` in `models/protocols.py` prüft Pflichtfelder (`id`, `email`, `is_active`, `is_superadmin`). `create_coreadmin` validiert + setzt `provider.user_model` beim Start.

   **DSGVO-Offen (aus Item 7):** Anonymize-on-request, Retention Policy, Audit-Log-Pseudonymisierung.
