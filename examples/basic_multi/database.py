import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///basic_multi.db")
os.environ.setdefault("MULTI_TENANT", "true")
# Default to header-based resolution so `curl -H "X-Tenant-Slug: acme" ...` works
# out of the box. Set TENANT_RESOLUTION_STRATEGY=subdomain in your env to use the
# acme.localhost:8000 subdomain flow described in README.md.
os.environ.setdefault("TENANT_RESOLUTION_STRATEGY", "header")
