"""Local web UI (Cursor-inspired dark theme)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.player_lookup import PlayerLookupService
from skyblock_agent.config import is_api_key_configured
from skyblock_agent.serializers import build_lookup_payload
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
        return {
            "status": "ok" if configured else "missing_api_key",
            "api_key_configured": configured,
            "message": message,
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
