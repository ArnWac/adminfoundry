# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2025-05-09

### Added
- `ModelAdmin` declarative registration with CRUD route generation
- Built-in admin UI (login, dashboard, list, detail, create, edit, delete)
- JWT authentication with refresh tokens and token blacklisting
- Role-based access control with per-model permission overrides
- Multi-tenancy support (header and subdomain resolution strategies)
- Tenant locale fields: `language`, `timezone`, `date_format`, `date_pattern`
- 3-tier locale hierarchy: `CoreAdminConfig` → Tenant → User preference
- i18n bundle (en, de) with `T()` lookup and `applyI18n()` for static templates
- Date/time formatting presets: locale, ISO, EU, US, custom strftime pattern
- Pluggable `AuthProvider` — subclass to integrate external auth
- `CoreAdminConfig.from_pyproject()` — read `[tool.adminfoundry]` from `pyproject.toml`
- Audit log middleware with `AuditLogAdmin`
- Password reset flow (email-based)
- Bulk actions and list-editable fields
- Dark mode, table density, and per-user UI preferences
- Health dashboard and Prometheus metrics endpoint
- CLI: `adminfoundry create-superadmin`, `adminfoundry doctor`
