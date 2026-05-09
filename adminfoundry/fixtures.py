"""Fixture loader — seed database from JSON or YAML files.

File format (JSON or YAML)::

    [
      {"model": "user", "fields": {"email": "admin@example.com", "is_superadmin": true}},
      {"model": "post", "fields": {"title": "Hello World", "published": true}}
    ]

Usage::

    # In lifespan or a CLI command:
    from adminfoundry.fixtures import load_fixture

    async with AsyncSessionLocal() as session:
        count = await load_fixture("fixtures/initial.json", session)
        print(f"Loaded {count} objects")

CLI::

    adminfoundry loaddata fixtures/initial.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


async def load_fixture(path: str | Path, session: Any) -> int:
    """Load fixture objects from *path* into *session*. Returns number of objects created."""
    import adminfoundry.admin_config  # noqa — ensure model registrations
    from adminfoundry.admin.registry import admin_site

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")

    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "YAML fixtures require PyYAML: pip install pyyaml"
            ) from exc
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    elif p.suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported fixture format: {p.suffix!r} (use .json or .yaml)")

    if not isinstance(data, list):
        raise ValueError("Fixture file must be a JSON/YAML list of {model, fields} objects")

    count = 0
    for entry in data:
        model_name: str = entry.get("model", "")
        fields: dict = entry.get("fields", {})

        if not model_name:
            raise ValueError(f"Fixture entry missing 'model' key: {entry}")

        ma = admin_site.get(model_name)
        if ma is None:
            raise ValueError(
                f"Model '{model_name}' not registered in admin_site. "
                "Ensure admin_config is imported before loading fixtures."
            )

        obj = ma.model(**fields)
        session.add(obj)
        count += 1

    await session.commit()
    return count


async def dump_fixture(model_name: str, session: Any, path: str | Path) -> int:
    """Dump all records of *model_name* to a JSON fixture file. Returns count."""
    from adminfoundry.admin.registry import admin_site
    from adminfoundry.admin.serializer import serializer
    from sqlalchemy import select

    ma = admin_site.get(model_name)
    if ma is None:
        raise ValueError(f"Model '{model_name}' not registered")

    items = (await session.execute(select(ma.model))).scalars().all()
    data = [
        {"model": model_name, "fields": serializer.serialize(obj, ma)}
        for obj in items
    ]

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return len(data)
