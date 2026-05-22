"""Errors raised by the extension lifecycle."""

from __future__ import annotations


class ExtensionError(Exception):
    """Base class for every extension-system failure."""


class DuplicateExtensionError(ExtensionError):
    """Two extensions tried to register under the same ``name``.

    Extension names are part of the registry's identity — duplicates
    would make ``runtime.extensions.get("foo")`` ambiguous and break
    extension-vs-extension navigation/permission contribution merges.
    """


class RegistryFrozenError(ExtensionError):
    """Attempted to mutate an extension-side registry after freeze.

    Raised by :class:`PermissionRegistry`, :class:`ContractContributionRegistry`,
    :class:`NavigationRegistry`, :class:`ProtectedFieldRegistry`, and
    :class:`ExtensionRegistry` itself. After ``create_admin()`` finishes,
    all registries are frozen — extensions must contribute during their
    declared lifecycle hooks, not at request time.
    """


class ExtensionDependencyError(ExtensionError):
    """An extension declared a dependency on another extension that isn't
    registered. Reserved for a future ``depends_on`` declaration; not
    raised in v1 (no extension uses dependencies yet)."""
