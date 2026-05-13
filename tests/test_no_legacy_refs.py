"""
Regression: no source/docs/config file may carry legacy `coreAdmin*` strings.

Excluded:
- .claude/ — IDE permission cache, not source.
- .git/, __pycache__/, *.db — local artifacts.
- This test file — it names the forbidden strings.
- tests/test_framework_boundary.py — its assertions intentionally reference `create_coreadmin`.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN = re.compile(r"coreAdmin_api|coreAdmin|coreadmin|core_admin")

EXCLUDE_DIRS = {".git", ".claude", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", "build", "dist"}
EXCLUDE_SUFFIX = {".db", ".pyc", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"}
EXCLUDE_FILES = {
    "tests/test_no_legacy_refs.py",
    "tests/test_framework_boundary.py",
}


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in EXCLUDE_SUFFIX:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        if rel in EXCLUDE_FILES:
            continue
        out.append(p)
    return out


def test_no_legacy_coreadmin_references():
    offenders: list[str] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN.search(line):
                rel = path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel}:{i}: {line.strip()[:140]}")

    assert not offenders, (
        "Legacy coreAdmin/coreadmin/core_admin references found:\n  "
        + "\n  ".join(offenders[:30])
        + (f"\n  ... ({len(offenders) - 30} more)" if len(offenders) > 30 else "")
    )
