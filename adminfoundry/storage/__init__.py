"""Storage SPI + filesystem backend (Roadmap P4).

Public surface:

* :class:`StorageBackend` — Protocol every backend implements.
* :class:`StoredObject` — neutral DTO returned by ``put`` / ``stat``.
* :class:`LocalFileStorage` — default filesystem implementation.
* :class:`StorageError` / :class:`ObjectNotFound` / :class:`StorageRejected`
  — exception hierarchy backends raise.

Cloud backends (S3, GCS, ...) live as installable extensions under
``adminfoundry.extensions.storage_*`` and depend only on this package
— they do **not** import ``boto3``/``google-cloud-storage`` at module
load time of any core module.
"""

from __future__ import annotations

from adminfoundry.storage.base import StorageBackend, StoredObject
from adminfoundry.storage.errors import (
    ObjectNotFound,
    StorageError,
    StorageRejected,
)
from adminfoundry.storage.local import LocalFileStorage

__all__ = [
    "LocalFileStorage",
    "ObjectNotFound",
    "StorageBackend",
    "StorageError",
    "StorageRejected",
    "StoredObject",
]
