"""
Single-tenant blog example.

Run:
    uvicorn examples.basic_single.app:app --reload

Admin UI: http://127.0.0.1:8000/admin-ui
"""
import os

import examples.basic_single.admin_config  # noqa: F401 — register admins

from contextlib import asynccontextmanager

from fastapi import FastAPI

from adminfoundry import create_admin, CoreAdminConfig
from examples.basic_single.seed import seed, print_banner


config = CoreAdminConfig(
    database_url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./basic_single.db"),
    secret_key=os.environ.get("SECRET_KEY", "dev-secret"),
    enable_multi_tenant=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed()
    print_banner()
    yield


app = create_admin(
    config=config,
    title="adminfoundry — basic_single",
    lifespan=lifespan,
)
