"""FastAPI routes for the web GUI.

Serves HTML pages using Jinja2 templates with vanilla JavaScript.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/gui", tags=["gui"])

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def setup_gui(app: FastAPI) -> None:
    """Mount static files and include GUI router.

    Call this during app initialization to enable the web GUI.

    Args:
        app: FastAPI application instance
    """
    # Mount static files
    static_dir = BASE_DIR / "static"
    if static_dir.exists():
        app.mount(
            "/gui/static",
            StaticFiles(directory=static_dir),
            name="gui_static",
        )

    # Include router
    app.include_router(router)


@router.get("", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Main generation page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "active_page": "home"},
    )


@router.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request) -> HTMLResponse:
    """Category browser page."""
    return templates.TemplateResponse(
        "categories.html",
        {"request": request, "active_page": "categories"},
    )


@router.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request) -> HTMLResponse:
    """Generation history/gallery page."""
    return templates.TemplateResponse(
        "gallery.html",
        {"request": request, "active_page": "gallery"},
    )


@router.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request) -> HTMLResponse:
    """Intelligent composition page."""
    return templates.TemplateResponse(
        "compose.html",
        {"request": request, "active_page": "compose"},
    )
