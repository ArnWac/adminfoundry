import asyncio
import typer
from sqlalchemy import select, text
from coreAdmin_api.database import AsyncSessionLocal, engine, get_or_create_tenant_engine
from coreAdmin_api.models.user import User
from coreAdmin_api.models.tenant import Tenant
from coreAdmin_api.auth import hash_password
from coreAdmin_api.settings import settings

app = typer.Typer()


@app.command()
def create_superadmin(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    full_name: str = typer.Option(None),
):
    """Create the first superadmin user."""
    asyncio.run(_create_superadmin(email, password, full_name))


async def _create_superadmin(email: str, password: str, full_name: str | None):
    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_superadmin=True,
        )
        session.add(user)
        await session.commit()
        typer.echo(f"Superadmin {email} created.")


@app.command()
def migrate_tenant(slug: str = typer.Argument(..., help="Tenant slug")):
    """Create PostgreSQL schema for a tenant and run tenant migrations."""
    asyncio.run(_migrate_tenant_schema(slug))


@app.command()
def migrate_all_tenants():
    """Create PostgreSQL schemas for all active tenants and run tenant migrations."""
    asyncio.run(_migrate_all_tenants())


async def _migrate_tenant_schema(slug: str):
    if "postgresql" not in settings.DATABASE_URL:
        typer.echo(f"[skip] non-PostgreSQL database — schema creation not applicable for {slug}")
        return

    schema_name = f"tenant_{slug}"
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    get_or_create_tenant_engine(schema_name)
    typer.echo(f"Schema {schema_name} ready.")


async def _migrate_all_tenants():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.is_active == True))  # noqa: E712
        tenants = result.scalars().all()

    if not tenants:
        typer.echo("No active tenants found.")
        return

    for tenant in tenants:
        await _migrate_tenant_schema(tenant.slug)


if __name__ == "__main__":
    app()
