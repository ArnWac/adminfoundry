---
name: adminfoundry is an internationally-used package
description: The project is designed as a package for international use — decisions about formatting, i18n, defaults, and configuration must account for diverse locales, timezones, and conventions
type: project
---

adminfoundry is written as an open, internationally-usable Python/FastAPI admin package — not a single-tenant internal tool.

**Why:** The user stated this explicitly as a standing constraint from this point forward.

**How to apply:**
- Default formats, labels, and behaviors must be locale-neutral or configurable
- Date/time display must be configurable (format + timezone) — no hardcoded locale assumptions
- API responses should use ISO 8601 timestamps (UTC)
- UI copy should avoid region-specific idioms
- Configuration surface (ModelAdmin, UIPreference, framework config) should expose internationalization knobs rather than baking in assumptions
- When adding new display features, ask: does this work for non-German, non-US users?
