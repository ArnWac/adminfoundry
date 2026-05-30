from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = _PACKAGE_ROOT / "templates"
STATIC_DIR = _PACKAGE_ROOT / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def get_static_app() -> StaticFiles:
    return StaticFiles(directory=str(STATIC_DIR))


def _template_context(
    request: Request,
    *,
    view: str,
    resource: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    runtime = request.app.state.adminfoundry
    config = runtime.config

    return {
        "config": config.to_safe_dict(),
        "admin_title": config.app_title,
        "admin_api_prefix": config.admin_api_prefix,
        "auth_api_prefix": config.auth_api_prefix,
        "admin_ui_path": config.admin_ui_path,
        "view": view,
        "resource": resource,
        "record_id": record_id,
    }


def _app(
    request: Request,
    *,
    view: str,
    resource: str | None = None,
    record_id: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "app.html",
        _template_context(
            request,
            view=view,
            resource=resource,
            record_id=record_id,
        ),
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def ui_root(request: Request):
    return RedirectResponse(url=f"{request.app.state.adminfoundry.config.admin_ui_path}/dashboard")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def ui_login(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        _template_context(request, view="login"),
    )


@router.get("/login-complete", response_class=HTMLResponse, include_in_schema=False)
async def ui_login_complete(request: Request):
    """Landing page for the OAuth fragment-redirect.

    The OAuth callback ends with ``302 /admin/login-complete#token=…``
    so the JWT lives in the URL fragment (never the query string).
    This page's JS reads it, stores it under the same localStorage
    key the rest of the UI uses, replaces the URL to clear the
    fragment, and bounces to ``return_to``.
    """
    return templates.TemplateResponse(
        request,
        "login_complete.html",
        _template_context(request, view="login-complete"),
    )


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def ui_dashboard(request: Request):
    return _app(request, view="dashboard")


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def ui_settings(request: Request):
    return _app(request, view="settings")


@router.get("/permissions", response_class=HTMLResponse, include_in_schema=False)
async def ui_permissions(request: Request):
    """Permission-matrix view (Roadmap 5.2b).

    Renders the matrix shell; the JS view fetches roles + permissions
    + assignments from ``GET /_permission_matrix`` and the user
    toggles cells. Mounted on a static path (NOT under
    ``/{resource}``) so the dynamic CRUD router can't shadow it.
    """
    return _app(request, view="permissions")


@router.get("/{resource}/new", response_class=HTMLResponse, include_in_schema=False)
async def ui_create(request: Request, resource: str):
    return _app(
        request,
        view="create",
        resource=resource,
    )


@router.get(
    "/{resource}/{record_id}/edit",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def ui_edit(request: Request, resource: str, record_id: str):
    return _app(
        request,
        view="edit",
        resource=resource,
        record_id=record_id,
    )


@router.get(
    "/{resource}/{record_id}/delete",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def ui_delete(request: Request, resource: str, record_id: str):
    return _app(
        request,
        view="delete",
        resource=resource,
        record_id=record_id,
    )


@router.get(
    "/{resource}/{record_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def ui_detail(request: Request, resource: str, record_id: str):
    return _app(
        request,
        view="detail",
        resource=resource,
        record_id=record_id,
    )


@router.get("/{resource}", response_class=HTMLResponse, include_in_schema=False)
async def ui_list(request: Request, resource: str):
    return _app(
        request,
        view="list",
        resource=resource,
    )
