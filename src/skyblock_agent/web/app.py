"""Local web UI (Cursor-inspired dark theme)."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from skyblock_agent.collectors.icon_client import IconClient
from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.market_collector import MarketCollector
from skyblock_agent.collectors.player_lookup import PlayerLookupService
from skyblock_agent.config import is_api_key_configured
from skyblock_agent.serializers import (
    build_auctions_payload,
    build_bazaar_payload,
    build_lookup_payload,
)
from skyblock_agent.storage.icon_index import (
    ensure_vanilla_icon_for_item,
    get_icon_path,
    get_icons_meta,
    get_vanilla_icon_path_for_item,
    has_icon,
    icons_are_available,
)
from skyblock_agent.storage.item_index import catalog_is_available, get_catalog_item, get_catalog_meta, search_items
from skyblock_agent.storage.tooltips_index import get_item_tooltip, get_tooltips_meta, tooltips_are_available
from skyblock_agent.storage.player_index import delete_player, list_players
from skyblock_agent.validation.api_recognizer import recognize_player_result

STATIC_DIR = Path(__file__).resolve().parent / "static"
_INDEX_PATH = STATIC_DIR / "index.html"
_ICON_CLIENT: IconClient | None = None


def _get_icon_client() -> IconClient:
    global _ICON_CLIENT
    if _ICON_CLIENT is None:
        _ICON_CLIENT = IconClient()
    return _ICON_CLIENT


def _resolve_icon_path(item_id: str, *, texture: str) -> Path | None:
    key = item_id.strip().upper()
    mode = texture.strip().lower()
    if mode == "vanilla":
        path = get_vanilla_icon_path_for_item(key)
        if path is None:
            path = ensure_vanilla_icon_for_item(key, _get_icon_client())
        return path
    return get_icon_path(key)


_ASSET_FILES = (
    "app.js",
    "market-browser.js",
    "item-icons.js",
    "item-tooltips.js",
    "profile-inventory.js",
    "profile-collections.js",
    "profile-catacombs.js",
    "tooltip-debug.js",
    "minetip.js",
    "styles.css",
    "minetip.css",
    "index.html",
)


def _asset_version() -> str:
    mtimes = [
        (STATIC_DIR / name).stat().st_mtime
        for name in _ASSET_FILES
        if (STATIC_DIR / name).is_file()
    ]
    return str(int(max(mtimes))) if mtimes else "1"


def _render_index_html() -> str:
    html = _INDEX_PATH.read_text(encoding="utf-8")
    version = _asset_version()
    return re.sub(r"\?v=\d+", f"?v={version}", html)


def create_app():
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse, HTMLResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError(
            'GUI dependencies are missing. Install with: pip install -e ".[gui]"'
        ) from exc

    app = FastAPI(title="Skyblock Agent", version="0.1.0")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        configured = is_api_key_configured()
        message = "ready" if configured else "Set HYPIXEL_API_KEY in .env (use /api new in-game)"
        items_meta = get_catalog_meta()
        items_available = catalog_is_available() and items_meta is not None
        icons_meta = get_icons_meta()
        icons_available = icons_are_available() and icons_meta is not None
        tooltips_meta = get_tooltips_meta()
        tooltips_available = tooltips_are_available() and tooltips_meta is not None
        return {
            "status": "ok" if configured else "missing_api_key",
            "api_key_configured": configured,
            "message": message,
            "items_catalog": {
                "available": items_available,
                "item_count": items_meta.item_count if items_meta else 0,
                "last_imported_at": items_meta.last_imported_at if items_meta else None,
                "hint": None
                if items_available
                else "Run sync-items.bat to download the item catalog (GUI does not auto-sync)",
            },
            "items_icons": {
                "available": icons_available,
                "icon_count": icons_meta.icon_count if icons_meta else 0,
                "coverage_pct": icons_meta.coverage_pct if icons_meta else 0.0,
                "last_imported_at": icons_meta.last_imported_at if icons_meta else None,
                "hint": None
                if icons_available
                else "Run sync-icons.bat to download item icons (requires item catalog first)",
            },
            "items_tooltips": {
                "available": tooltips_available,
                "item_count": tooltips_meta.item_count if tooltips_meta else 0,
                "sources": tooltips_meta.sources if tooltips_meta else {},
                "last_imported_at": tooltips_meta.last_imported_at if tooltips_meta else None,
                "hint": None
                if tooltips_available
                else "Run sync-tooltips.bat to download NEU/wiki tooltips (GUI does not auto-sync)",
            },
        }

    @app.get("/api/items")
    def list_items(
        q: Optional[str] = Query(default=None, description="Search by name or id"),
        category: Optional[str] = Query(default=None, description="Filter by category"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, object]:
        if not catalog_is_available():
            raise HTTPException(
                status_code=503,
                detail="Item catalog not imported. Run sync-items.bat or: skyblock-agent items import",
            )
        items = search_items(q or "", category=category, limit=limit)
        for item in items:
            item["has_icon"] = has_icon(str(item.get("id") or ""))
        meta = get_catalog_meta()
        return {
            "items": items,
            "count": len(items),
            "meta": meta.to_dict() if meta else None,
        }

    @app.get("/api/items/{item_id}/icon")
    def item_icon(
        item_id: str,
        texture: str = Query(default="official", description="official (SkyBlock) or vanilla (Minecraft material)"),
    ) -> FileResponse:
        mode = texture.strip().lower()
        if mode not in {"official", "vanilla"}:
            raise HTTPException(status_code=400, detail="texture must be official or vanilla")

        path = _resolve_icon_path(item_id, texture=mode)
        if path is None:
            if mode == "vanilla":
                raise HTTPException(
                    status_code=404,
                    detail="Vanilla icon not found for this item (missing material or texture).",
                )
            raise HTTPException(status_code=404, detail="Icon not found. Run sync-icons.bat.")
        return FileResponse(path, media_type="image/png")

    @app.get("/api/items/{item_id}/tooltip")
    def item_tooltip(item_id: str) -> dict[str, object]:
        if not tooltips_are_available():
            raise HTTPException(
                status_code=503,
                detail="Tooltip cache not imported. Run sync-tooltips.bat or: skyblock-agent items tooltips import",
            )
        tooltip = get_item_tooltip(item_id.strip().upper())
        if tooltip is None:
            catalog = get_catalog_item(item_id.strip().upper())
            if catalog:
                return {
                    "item_id": catalog.get("id"),
                    "found": False,
                    "catalog": catalog,
                }
            raise HTTPException(status_code=404, detail="Tooltip not found for item")
        return {"item_id": item_id.strip().upper(), "found": True, "tooltip": tooltip}

    def _http_error(exc: Exception) -> HTTPException:
        if isinstance(exc, RuntimeError):
            return HTTPException(status_code=503, detail=str(exc))
        if isinstance(exc, HypixelApiError):
            code = exc.status_code or 400
            if code in (403, 401):
                return HTTPException(status_code=503, detail=str(exc))
            if code == 429:
                return HTTPException(status_code=429, detail=str(exc))
            return HTTPException(status_code=400, detail=str(exc))
        return HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/lookup/{username}")
    def lookup_player(
        username: str,
        profile: Optional[str] = Query(default=None, description="Profile cute name"),
    ) -> dict[str, object]:
        try:
            with PlayerLookupService() as service:
                lookup = service.lookup(username, profile_name=profile)
            report = recognize_player_result(lookup.profile)
            return build_lookup_payload(lookup, report)
        except (RuntimeError, HypixelApiError) as exc:
            raise _http_error(exc) from exc

    @app.get("/api/players")
    def imported_players() -> dict[str, object]:
        records = list_players()
        return {
            "players": [record.to_dict() for record in records],
            "count": len(records),
        }

    @app.delete("/api/players/{username}")
    def remove_player(username: str) -> dict[str, object]:
        if not delete_player(username):
            raise HTTPException(status_code=404, detail="Player not found in import index")
        return {"deleted": True, "username": username}

    @app.get("/api/profile/{username}")
    def fetch_profile(
        username: str,
        profile: Optional[str] = Query(default=None, description="Profile cute name"),
    ) -> dict[str, object]:
        return lookup_player(username, profile)

    @app.get("/api/bazaar")
    def fetch_bazaar(
        q: Optional[str] = Query(default=None, description="Filter by product id or name"),
        category: Optional[str] = Query(default=None, description="Category filter"),
        sort: str = Query(default="name", pattern="^(name|sell|buy|spread)$"),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=48, ge=1, le=500),
    ) -> dict[str, object]:
        try:
            with MarketCollector() as collector:
                snapshot = collector.search_bazaar(
                    q or "",
                    category=category or "",
                    sort=sort,
                )
            return build_bazaar_payload(
                snapshot,
                query=q or "",
                category=category or "",
                sort=sort,
                offset=offset,
                limit=limit,
            )
        except (RuntimeError, HypixelApiError) as exc:
            raise _http_error(exc) from exc

    @app.get("/api/bazaar/categories")
    def bazaar_categories() -> dict[str, object]:
        meta = get_catalog_meta()
        categories = ["ENCHANTMENT", "OTHER"]
        if meta:
            categories = ["ENCHANTMENT"] + [c for c in meta.categories if c] + ["OTHER"]
        return {"categories": categories}

    @app.get("/api/auctions")
    def fetch_auctions(
        page: int = Query(default=0, ge=0),
        q: Optional[str] = Query(default=None, description="Filter item name on this page"),
        category: Optional[str] = Query(default=None, description="AH category"),
        bin_only: bool = Query(default=False),
        sort: str = Query(default="price", pattern="^(price|name|tier)$"),
        limit: int = Query(default=48, ge=1, le=1000),
    ) -> dict[str, object]:
        try:
            with MarketCollector() as collector:
                result = collector.search_auctions_page(
                    page,
                    q or "",
                    bin_only=bin_only,
                    category=category or "",
                    sort=sort,
                )
            return build_auctions_payload(
                result,
                query=q or "",
                bin_only=bin_only,
                category=category or "",
                sort=sort,
                limit=limit,
            )
        except (RuntimeError, HypixelApiError) as exc:
            raise _http_error(exc) from exc

    @app.middleware("http")
    async def disable_static_cache(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse(
            _render_index_html(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def run(host: str = "127.0.0.1", port: int = 8765, *, log_level: str = "info") -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            'GUI dependencies are missing. Install with: pip install -e ".[gui]"'
        ) from exc

    uvicorn.run(create_app(), host=host, port=port, log_level=log_level)
