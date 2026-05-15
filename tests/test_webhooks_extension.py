"""WebhookExtension contract tests.

Verifies that WebhookExtension implements ExtensionBase correctly and that
the existing dispatcher (register/clear) is still accessible.
"""
from __future__ import annotations


def test_webhook_extension_is_extension_base():
    from adminfoundry.extensions import ExtensionBase
    from adminfoundry.extensions.webhooks import WebhookExtension

    assert issubclass(WebhookExtension, ExtensionBase)
    ext = WebhookExtension()
    assert ext.name == "webhooks"
    assert isinstance(ext.version, str)


def test_webhook_extension_declares_models():
    from adminfoundry.extensions.webhooks import WebhookExtension
    from adminfoundry.extensions.webhooks.models import WebhookDelivery, WebhookSubscription

    ext = WebhookExtension()
    models = ext.get_models()
    assert WebhookSubscription in models
    assert WebhookDelivery in models


def test_webhook_extension_admin_registrations():
    from adminfoundry.extensions.webhooks import WebhookExtension
    from adminfoundry.admin.model_admin import ModelAdmin

    ext = WebhookExtension()
    registrations = ext.get_admin_registrations()
    assert len(registrations) >= 1
    assert all(isinstance(r, ModelAdmin) for r in registrations)


def test_webhook_extension_health_check():
    from adminfoundry.extensions.webhooks import WebhookExtension

    ext = WebhookExtension()
    health = ext.health_check()
    assert health["status"] == "ok"
    assert "registered_targets" in health


def test_imperative_register_and_clear():
    from adminfoundry.extensions import webhooks

    webhooks.clear()
    assert len(webhooks._targets) == 0


def test_create_admin_with_webhook_extension():
    from adminfoundry import create_admin, CoreAdminConfig
    from adminfoundry.extensions.webhooks import WebhookExtension

    app = create_admin(config=CoreAdminConfig(extensions=[WebhookExtension()]))
    runtime = app.state.adminfoundry
    assert "webhooks" in runtime.extension_registry.names()
