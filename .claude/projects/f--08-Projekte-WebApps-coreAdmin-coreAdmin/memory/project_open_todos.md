---
name: Offene Todos
description: Bekannte Lücken und offene Features die noch nicht implementiert sind
type: project
---

## UI / i18n

1. **Action-Labels und Column-Header nicht übersetzt** — Dynamisch generierte Inhalte aus der `ModelAdmin`-Konfiguration erscheinen auf Englisch, egal welche Sprache eingestellt ist:
   - `list_display`-Spaltentitel (werden aus Feldnamen per `_prettify()` erzeugt, kein i18n-Lookup)
   - `actions[].label` (fixer String im Python-Code)
   - `computed_fields`-Spaltenköpfe
   - Inline-Relations-Titel (`rel.label`)

   **Lösungsansatz:** `ModelAdmin` um `labels`-Dict erweitern (`labels = {"title": {"en": "Title", "de": "Titel"}}`). Alternativ: beim `admin_site.register()` eine Übersetzungsfunktion einbinden, die Labels sprachneutral definiert und per i18n-Katalog übersetzt. JS-Seite muss dann den aktiven Locale-Key berücksichtigen.

## DSGVO (aus Soft-Delete / Pluggable User-Model)

2. **Anonymize-on-request** — PII-Felder in soft-deleted Records durch Platzhalter ersetzen (z. B. `anonymized@gdpr.invalid`) statt Daten zu behalten.

3. **Retention Policy** — `soft_delete_retention_days` auf `ModelAdmin` — automatische Bereinigung nach X Tagen (Cronjob oder Admin-Action).

4. **Audit-Log-Anonymisierung** — GDPR-Delete-Workflow soll E-Mail/Namen im `AuditLog` durch pseudonymisierte ID ersetzen, damit personenbezogene Daten auch aus dem Log verschwinden.
