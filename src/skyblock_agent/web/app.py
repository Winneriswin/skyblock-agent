"""Local web UI (Cursor-inspired dark theme)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.market_collector import MarketCollector
from skyblock_agent.collectors.player_lookup import PlayerLookupService
from skyblock_agent.config import is_api_key_configured
from skyblock_agent.serializers import (
    build_auctions_payload,
    build_bazaar_payload,
    build_lookup_payload,
)
from skyblock_agent.storage.item_index import catalog_is_available, get_catalog_meta, search_items
from skyblock_agent.storage.player_index import list_players
from skyblock_agent.validation.api_recognizer import recognize_player_result

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app():
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse
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
        meta = get_catalog_meta()
        return {
            "items": items,
            "count": len(items),
            "meta": meta.to_dict() if meta else None,
        }

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
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            'GUI dependencies are missing. Install with: pip install -e ".[gui]"'
        ) from exc

    uvicorn.run(create_app(), host=host, port=port, log_level="info")
