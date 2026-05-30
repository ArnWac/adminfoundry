"""Notifier SPI (Roadmap P4.5).

Public surface:

* :class:`Notifier` — marker Protocol every typed notifier extends.
* :class:`NotifierRegistry` — runtime container, exposed as
  ``runtime.notifiers``.

Typed notifiers live next to their publishers — for example
:class:`~adminfoundry.auth.password_reset.PasswordResetNotifier` lives
in :mod:`adminfoundry.auth.password_reset`. Importing them from this
package is intentionally NOT supported: it would create import cycles
because publishers (like the auth router) depend on this module while
defining their notifier types. See
:mod:`adminfoundry.notifications.base` for the "how to add a new
notification type" recipe.
"""

from __future__ import annotations

from adminfoundry.notifications.base import Notifier, NotifierRegistry

__all__ = [
    "Notifier",
    "NotifierRegistry",
]
