"""PR-7 invariants: docs + examples + deployment artifacts.

These tests guard against three classes of regression:

* a doc claiming to live at `docs/<name>.md` actually exists,
* the bundled example imports + registers cleanly against the current
  ModelAdmin API (catches the historical bug where it used dropped
  attrs like ``filter_fields`` / ``fieldsets`` / ``computed_fields``),
* a flagship deployment artifact (``Dockerfile``, ``.env.example``,
  ``docker-compose.yml``) is present at the repo root.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"


# --- docs presence ---


@pytest.mark.parametrize(
    "filename",
    [
        "architecture.md",
        "security.md",
        "tenancy.md",
        "model-admin.md",
        "deployment.md",
    ],
)
def test_required_doc_exists(filename):
    path = DOCS_DIR / filename
    assert path.exists(), f"Missing doc: docs/{filename}"
    assert path.read_text(encoding="utf-8").strip(), f"docs/{filename} is empty"


def test_no_legacy_doc_left():
    """Old roadmap / protected-fields pages were deleted in PR-7."""
    assert not (DOCS_DIR / "protected-fields.md").exists()
    assert not (DOCS_DIR / "roadmap-postgres-tenancy.md").exists()


# --- README ---


def test_readme_exists_and_mentions_v1_api():
    readme = PROJECT_ROOT / "README.md"
    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert "create_admin" in content
    assert "CoreAdminConfig" in content
    assert "ModelAdmin" in content


def test_readme_does_not_reference_dropped_apis():
    """The historical README referenced `admin_site`, `AuthProvider`,
    `adminfoundry.settings` etc. PR-7 rewrites it; this test guards the
    rewrite from drifting back."""
    content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    # Use word-boundary checks so unrelated occurrences aren't false hits.
    assert not re.search(r"\badmin_site\b", content)
    assert not re.search(r"\bAuthProvider\b", content)
    assert not re.search(r"adminfoundry\.settings\b", content)


# --- deployment artifacts ---


@pytest.mark.parametrize(
    "filename",
    ["Dockerfile", ".env.example", "docker-compose.yml"],
)
def test_deployment_artifact_exists(filename):
    path = PROJECT_ROOT / filename
    assert path.exists(), f"Missing deployment artifact: {filename}"
    assert path.read_text(encoding="utf-8").strip(), f"{filename} is empty"


def test_env_example_lists_required_vars():
    content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ADMINFOUNDRY_DATABASE_URL" in content
    assert "ADMINFOUNDRY_SECRET_KEY" in content


# --- example app ---


def test_basic_single_example_admin_config_imports():
    """The example must import without raising — catches stale attrs."""
    mod = importlib.import_module("examples.basic_single.admin_config")
    assert hasattr(mod, "register")
    assert hasattr(mod, "PostAdmin")


def test_basic_single_example_uses_only_supported_attrs():
    """Any ModelAdmin subclass declared in the example must only set
    attributes that ``ModelAdmin`` actually supports. Catches dropped
    attrs like ``filter_fields``, ``fieldsets``, ``computed_fields``."""
    from adminfoundry import ModelAdmin
    from examples.basic_single.admin_config import PostAdmin

    supported = set(vars(ModelAdmin).keys())
    declared = {name for name in vars(PostAdmin).keys() if not name.startswith("_")}
    extras = declared - supported
    # `model` is the only required class attr that ModelAdmin itself
    # declares via class annotation rather than a value, so it shows up
    # in PostAdmin's dict but not in ModelAdmin's vars on older Pythons.
    extras.discard("model")
    assert not extras, (
        f"PostAdmin sets attrs not present on ModelAdmin: {sorted(extras)}. "
        "PR-7 dropped these — update the example."
    )


def test_basic_single_example_registers_against_real_registry():
    """Round-trip: invoking `register(AdminRegistry())` must not raise
    and must produce at least one registered admin."""
    from adminfoundry import AdminRegistry
    from examples.basic_single.admin_config import register

    registry = AdminRegistry()
    register(registry)
    assert registry.all(), "register() left the registry empty"
    names = [a.model_name for a in registry.all()]
    assert "posts" in names
