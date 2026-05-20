"""Packaging sanity tests (plan §PR-6).

We do NOT actually build a wheel here — that's CI work. These tests cover
the static invariants:

* py.typed marker exists where pyproject says it does.
* The package-data globs in pyproject.toml resolve to real files on disk
  (catches the historical bug where ``templates/**/*`` matched nothing
  because the templates live under ``ui/templates/``).
* The CLI ``console_scripts`` entrypoint is importable and runnable.
* No module performs DB / env-var side effects at import time.
* The version string is exposed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

try:  # Python 3.11+ standard lib
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
ADMINFOUNDRY = PROJECT_ROOT / "adminfoundry"


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


# --- py.typed ---


def test_py_typed_marker_exists():
    """PEP 561: the marker file must ship so downstream type-checkers
    pick up our annotations."""
    assert (ADMINFOUNDRY / "py.typed").exists()


def test_py_typed_listed_in_package_data(pyproject):
    pkg_data = pyproject["tool"]["setuptools"]["package-data"]["adminfoundry"]
    assert "py.typed" in pkg_data


# --- package-data globs resolve ---


def test_ui_template_glob_matches_real_files(pyproject):
    pkg_data = pyproject["tool"]["setuptools"]["package-data"]["adminfoundry"]
    template_globs = [g for g in pkg_data if "templates" in g]
    assert template_globs, "Expected at least one templates/** glob"

    # Resolve each glob relative to the adminfoundry package and assert
    # we hit at least one file.
    found: list[Path] = []
    for glob in template_globs:
        found.extend(ADMINFOUNDRY.glob(glob))
    assert found, (
        f"Package-data globs {template_globs!r} matched ZERO files. "
        "Templates likely moved without updating pyproject.toml."
    )

    # Sanity: app.html + login.html must be among them.
    names = {p.name for p in found}
    assert "app.html" in names
    assert "login.html" in names


def test_ui_static_glob_matches_real_files(pyproject):
    pkg_data = pyproject["tool"]["setuptools"]["package-data"]["adminfoundry"]
    static_globs = [g for g in pkg_data if "static" in g]
    assert static_globs

    found: list[Path] = []
    for glob in static_globs:
        found.extend(ADMINFOUNDRY.glob(glob))
    names = {p.name for p in found}
    assert {"admin.css", "admin.js"}.issubset(names)


# --- CLI entrypoint ---


def test_console_scripts_entrypoint_declared(pyproject):
    scripts = pyproject["project"]["scripts"]
    assert "adminfoundry" in scripts
    assert scripts["adminfoundry"] == "adminfoundry.cli:app"


def test_console_scripts_target_is_importable():
    """``adminfoundry.cli:app`` must resolve to a Typer app instance."""
    cli_module = importlib.import_module("adminfoundry.cli")
    assert hasattr(cli_module, "app"), "adminfoundry.cli must expose 'app'"


def test_console_scripts_app_runs_help():
    from typer.testing import CliRunner

    from adminfoundry.cli import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0


# --- import-time side-effect surface ---


@pytest.mark.parametrize(
    "module_name",
    [
        "adminfoundry",
        "adminfoundry.actions",
        "adminfoundry.audit",
        "adminfoundry.auth",
        "adminfoundry.authz",
        "adminfoundry.builtins",
        "adminfoundry.cli",
        "adminfoundry.contract",
        "adminfoundry.core",
        "adminfoundry.crud",
        "adminfoundry.db",
        "adminfoundry.models",
        "adminfoundry.registry",
        "adminfoundry.root",
        "adminfoundry.schemas",
        "adminfoundry.security",
        "adminfoundry.tenancy",
        "adminfoundry.ui",
    ],
)
def test_subpackage_imports_without_env_vars(module_name, monkeypatch):
    """``import adminfoundry.X`` must NOT call os.environ for required vars.
    Only ``CoreAdminConfig.from_env()`` may do that, and it's an explicit call.
    """
    monkeypatch.delenv("ADMINFOUNDRY_DATABASE_URL", raising=False)
    monkeypatch.delenv("ADMINFOUNDRY_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Force re-import in case another test pre-imported it
    sys.modules.pop(module_name, None)
    importlib.import_module(module_name)


# --- version ---


def test_version_string_present():
    import adminfoundry

    assert isinstance(adminfoundry.__version__, str)
    assert adminfoundry.__version__  # non-empty


def test_pyproject_version_matches_runtime(pyproject):
    runtime_version = importlib.import_module("adminfoundry").__version__
    declared_version = pyproject["project"]["version"]
    assert runtime_version == declared_version
