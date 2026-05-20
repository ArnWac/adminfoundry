from __future__ import annotations

from dataclasses import dataclass, field

from adminfoundry.core.config import CoreAdminConfig
from adminfoundry.db.session import DatabaseManager
from adminfoundry.registry import AdminRegistry


@dataclass(slots=True)
class AdminRuntime:
    config: CoreAdminConfig
    db: DatabaseManager
    registry: AdminRegistry = field(default_factory=AdminRegistry)


def get_runtime(app) -> AdminRuntime:
    return app.state.adminfoundry
